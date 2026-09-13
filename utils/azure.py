"""ADLS com token Azure CLI; nenhuma chave de Storage."""
import json
import logging

from utils.config import DATASETS, SOURCE_REVISION, bronze_path
from utils.ingestion import download


def filesystem(config):
    from azure.identity import AzureCliCredential
    from azure.storage.filedatalake import DataLakeServiceClient

    return DataLakeServiceClient(config["account_url"], credential=AzureCliCredential(
        process_timeout=30)).get_file_system_client(config["filesystem"])


def ingest(config, day, revision=SOURCE_REVISION):
    fs = filesystem(config)
    from azure.core.exceptions import ResourceNotFoundError

    try:
        previous = fs.get_file_client(f"load_date={day}/manifest.json").download_file().readall()
        if json.loads(previous)["revision"] != revision:
            raise ValueError("Use outra load_date para uma revisão diferente da fonte")
    except ResourceNotFoundError:
        pass
    manifest = {"load_date": day, "revision": revision, "files": []}
    for dataset in DATASETS:
        data, metadata = download(dataset, revision)
        path = bronze_path(day, dataset)
        fs.get_directory_client(f"load_date={day}/{dataset}").create_directory()
        fs.get_file_client(path).upload_data(data, overwrite=True,
                                           metadata={"sha256": metadata["sha256"]})
        manifest["files"].append({**metadata, "key": path})
    fs.get_file_client(f"load_date={day}/manifest.json").upload_data(
        json.dumps(manifest).encode(), overwrite=True)
    logging.info("Bronze Azure: %s", manifest)
    return manifest
