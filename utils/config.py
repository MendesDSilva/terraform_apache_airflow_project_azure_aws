"""Configuração pública, separada das sessões de autenticação."""
import json
import os
import re
from datetime import date
from pathlib import Path

SOURCE_REVISION = "42efa594aaf3ef5b24877c7b61f1c1d7abc280cc"
DATASETS = ("bookings", "passengers", "airports")
CATALOGS = {"aws": "aws-airflow-gold", "azure": "azure-airflow-gold"}


def load_date(value):
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        raise ValueError("load_date deve ser AAAA-MM-DD")
    return date.fromisoformat(value).isoformat()


def bronze_path(day, dataset):
    if dataset not in DATASETS:
        raise ValueError("Dataset desconhecido")
    return f"load_date={load_date(day)}/{dataset}/{dataset}.csv"


def read_config():
    path = Path(os.getenv("PIPELINE_CONFIG", "/opt/airflow/.runtime/config.json"))
    if not path.exists():
        raise ValueError("Exporte os outputs Terraform com scripts/export_config.py")
    return json.loads(path.read_text(encoding="utf-8"))


def validate_config(config, clouds):
    if clouds not in ("aws", "azure", "both"):
        raise ValueError("clouds deve ser aws, azure ou both")
    revision = config.get("source_revision", SOURCE_REVISION)
    if not re.fullmatch(r"[0-9a-f]{40}", revision):
        raise ValueError("source_revision deve ser um commit SHA completo")
    selected = ["aws", "azure"] if clouds == "both" else [clouds]
    required = {
        "aws": ("bucket", "region", "glue_job", "crawler", "database", "workgroup"),
        "azure": ("account_url", "filesystem"),
    }
    for cloud in selected:
        for key in required[cloud]:
            if not config.get(cloud, {}).get(key):
                raise ValueError(f"Configuração ausente: {cloud}.{key}")
        if not config.get("databricks", {}).get("jobs", {}).get(cloud):
            raise ValueError(f"Configuração ausente: databricks.jobs.{cloud}")
    return selected
