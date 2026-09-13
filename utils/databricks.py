"""Ponte explícita para Free Edition: arquivos das clouds -> volumes gerenciados."""
import hashlib
import io
import json
import logging
import uuid

from utils.config import CATALOGS
from utils.ingestion import MAX_BYTES, checksum
from utils.polling import wait_terminal


def workspace():
    # O PATH base do Airflow inclui /root/bin, inacessível ao usuário airflow.
    # Remova-o para que o SDK use a CLI instalada em /usr/local/bin.
    import os

    from databricks.sdk import WorkspaceClient

    from utils.config import read_config
    os.environ["PATH"] = ":".join(p for p in os.environ.get("PATH", "").split(":") if p != "/root/bin")
    return WorkspaceClient(host=read_config().get("databricks", {}).get("host"))


def publish_files(ws, cloud, day, files):
    """files gera (nome, bytes); manifesto final é o marcador de completude."""
    base = f"/Volumes/{CATALOGS[cloud]}/staging/inbound/load_date={day}/{uuid.uuid4().hex}"
    ws.files.create_directory(base)
    manifest = {"cloud": cloud, "load_date": day, "files": []}
    for name, data in files:
        if "/" in name or name in (".", "..") or not data:
            raise ValueError("Arquivo de transferência inválido")
        if len(data) > MAX_BYTES:
            raise ValueError("Arquivo ultrapassou limite didático de 20 MiB")
        target = f"{base}/{name}"
        ws.files.upload(target, io.BytesIO(data), overwrite=True)
        # Releitura garante conteúdo íntegro antes de publicar o manifesto.
        response = ws.files.download(target)
        with response.contents as stream:
            actual = stream.read(MAX_BYTES + 1)
        if checksum(actual) != checksum(data):
            raise ValueError(f"Checksum de transferência inválido: {name}")
        manifest["files"].append({"name": name, "sha256": checksum(data), "bytes": len(data)})
    if not manifest["files"]:
        raise ValueError("Nenhum arquivo para transferir")
    ws.files.upload(f"{base}/manifest.json", io.BytesIO(json.dumps(manifest).encode()))
    return {"path": base, "load_date": day, "cloud": cloud}


def transfer_aws(config, silver):
    from utils.aws import client

    s3 = client("s3", config)

    def files():
        for page in s3.get_paginator("list_objects_v2").paginate(
                Bucket=config["bucket"], Prefix=silver["prefix"]):
            for obj in page.get("Contents", []):
                if obj["Key"].endswith(".parquet"):
                    if obj["Size"] > MAX_BYTES:
                        raise ValueError("Parquet excede limite de transferência")
                    body = s3.get_object(Bucket=config["bucket"], Key=obj["Key"])["Body"]
                    with body:
                        data = body.read(MAX_BYTES + 1)
                    yield obj["Key"].rsplit("/", 1)[-1], data

    return publish_files(workspace(), "aws", silver["load_date"], files())


def transfer_azure(config, manifest):
    from utils.azure import filesystem

    fs = filesystem(config)

    def files():
        for item in manifest["files"]:
            file = fs.get_file_client(item["key"])
            if file.get_file_properties().size > MAX_BYTES:
                raise ValueError("CSV excede limite de transferência")
            data = file.download_file().readall()
            if checksum(data) != item["sha256"]:
                raise ValueError("Bronze Azure mudou após ingestão")
            yield item["key"].rsplit("/", 1)[-1], data

    return publish_files(workspace(), "azure", manifest["load_date"], files())


def run_job(job_id, transfer, execution_id):
    ws = workspace()
    token = hashlib.sha256(f"{execution_id}:{transfer['path']}".encode()).hexdigest()
    response = ws.jobs.run_now(job_id=int(job_id), idempotency_token=token,
                               job_parameters={"input_path": transfer["path"],
                                               "load_date": transfer["load_date"]})
    run_id = response.run_id
    logging.info("Databricks run_id=%s", run_id)

    def state(run):
        if run.state.result_state:
            return run.state.result_state.value
        return run.state.life_cycle_state.value

    try:
        wait_terminal(lambda: ws.jobs.get_run(run_id), state, {"SUCCESS"},
                      {"FAILED", "TIMEDOUT", "CANCELED", "INTERNAL_ERROR", "SKIPPED",
                       "SUCCESS_WITH_FAILURES", "UPSTREAM_FAILED", "EXCLUDED"}, timeout=2400)
    except TimeoutError:
        ws.jobs.cancel_run(run_id)
        raise
    return {"run_id": run_id, "cloud": transfer["cloud"]}
