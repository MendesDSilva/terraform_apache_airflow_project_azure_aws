"""Operações AWS chamadas apenas dentro das tasks."""
import json
import logging
import uuid

from utils.config import DATASETS, SOURCE_REVISION, bronze_path
from utils.ingestion import download
from utils.polling import wait_terminal


def client(service, config):
    import boto3
    from botocore.config import Config

    return boto3.client(service, region_name=config["region"], config=Config(
        connect_timeout=10, read_timeout=60, retries={"max_attempts": 3}))


def ingest(config, day, revision=SOURCE_REVISION):
    s3 = client("s3", config)
    from botocore.exceptions import ClientError

    try:
        previous = s3.get_object(Bucket=config["bucket"], Key=f"bronze/load_date={day}/manifest.json")
        with previous["Body"] as stream:
            if json.loads(stream.read())["revision"] != revision:
                raise ValueError("Use outra load_date para uma revisão diferente da fonte")
    except ClientError as exc:
        if exc.response["Error"]["Code"] not in ("NoSuchKey", "404"):
            raise
    manifest = {"load_date": day, "revision": revision, "files": []}
    for dataset in DATASETS:
        data, metadata = download(dataset, revision)
        key = "bronze/" + bronze_path(day, dataset)
        s3.put_object(Bucket=config["bucket"], Key=key, Body=data,
                      Metadata={"sha256": metadata["sha256"], "revision": revision})
        manifest["files"].append({**metadata, "key": key})
    s3.put_object(Bucket=config["bucket"], Key=f"bronze/load_date={day}/manifest.json",
                  Body=json.dumps(manifest).encode())
    logging.info("Bronze AWS: %s", manifest)
    return manifest


def run_glue(config, day):
    glue = client("glue", config)
    # Cada tentativa escreve isoladamente; apenas o caminho concluído vira XCom.
    prefix = f"silver/bookings_enriched/load_date={day}/attempt={uuid.uuid4().hex}/"
    run = glue.start_job_run(JobName=config["glue_job"], Arguments={
        "--load_date": day, "--bucket": config["bucket"],
        "--output_path": f"s3://{config['bucket']}/{prefix}"})["JobRunId"]
    logging.info("Glue run_id=%s", run)
    try:
        wait_terminal(lambda: glue.get_job_run(JobName=config["glue_job"], RunId=run),
                      lambda r: r["JobRun"]["JobRunState"], {"SUCCEEDED"},
                      {"FAILED", "STOPPED", "TIMEOUT", "ERROR", "EXPIRED"}, timeout=2400)
    except TimeoutError:
        glue.batch_stop_job_run(JobName=config["glue_job"], JobRunIds=[run])
        raise
    return {"prefix": prefix, "run_id": run, "load_date": day}


def query_athena(config, silver):
    glue = client("glue", config)
    # O crawler expõe um snapshot por vez, sem varrer tentativas antigas.
    glue.update_crawler(Name=config["crawler"], Targets={"S3Targets": [
        {"Path": f"s3://{config['bucket']}/{silver['prefix']}"}]})
    glue.start_crawler(Name=config["crawler"])
    result = wait_terminal(lambda: glue.get_crawler(Name=config["crawler"]),
                           lambda r: r["Crawler"]["State"], {"READY"}, set(), timeout=900)
    if result["Crawler"].get("LastCrawl", {}).get("Status") != "SUCCEEDED":
        raise RuntimeError("Crawler não concluiu com sucesso")
    tables = []
    for page in glue.get_paginator("get_tables").paginate(DatabaseName=config["database"]):
        tables.extend(t for t in page["TableList"] if
                      t.get("StorageDescriptor", {}).get("Location", "").rstrip("/") ==
                      f"s3://{config['bucket']}/{silver['prefix']}".rstrip("/"))
    if len(tables) != 1:
        raise RuntimeError("Esperada uma tabela para o snapshot atual do crawler")
    table = tables[0]["Name"].replace('"', '""')
    athena = client("athena", config)
    query_id = athena.start_query_execution(
        QueryString=f'SELECT count(*) FROM "{table}"',
        QueryExecutionContext={"Database": config["database"]},
        WorkGroup=config["workgroup"])["QueryExecutionId"]
    try:
        wait_terminal(lambda: athena.get_query_execution(QueryExecutionId=query_id),
                      lambda r: r["QueryExecution"]["Status"]["State"], {"SUCCEEDED"},
                      {"FAILED", "CANCELLED"}, timeout=300)
    except TimeoutError:
        athena.stop_query_execution(QueryExecutionId=query_id)
        raise
    rows = athena.get_query_results(QueryExecutionId=query_id)["ResultSet"]["Rows"]
    count = int(rows[1]["Data"][0]["VarCharValue"])
    if count <= 0:
        raise ValueError("Athena retornou Silver vazia")
    return {"query_id": query_id, "rows": count, "table": tables[0]["Name"]}
