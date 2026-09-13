"""Orquestração somente; clientes e regras de dados ficam fora desta DAG."""
from datetime import datetime, timedelta, timezone

from airflow.sdk import Param, TaskGroup, dag, get_current_context, task
from airflow.sdk.exceptions import AirflowFailException, AirflowSkipException


def checked(call, *args):
    # Erros de contrato não melhoram com uma nova tentativa.
    try:
        return call(*args)
    except ValueError as exc:
        raise AirflowFailException(str(exc)) from exc


@dag(dag_id="multi_cloud_data_pipeline", schedule=None, catchup=False, max_active_runs=1,
     start_date=datetime(2025, 1, 1, tzinfo=timezone.utc),
     default_args={"retries": 2, "retry_delay": timedelta(seconds=30),
                   "retry_exponential_backoff": True, "execution_timeout": timedelta(minutes=50)},
     params={"clouds": Param("both", enum=["aws", "azure", "both"]),
             "load_date": Param(None, type=["null", "string"], format="date")},
     tags=["portfolio", "multicloud"])
def pipeline():
    @task
    def prepare():
        from utils.config import SOURCE_REVISION, load_date, read_config, validate_config

        context = get_current_context()
        config = read_config()
        selected = checked(validate_config, config, context["params"]["clouds"])
        day = checked(load_date, context["params"]["load_date"] or
                      context["dag_run"].start_date.date().isoformat())
        return {"clouds": selected, "load_date": day,
                "revision": config.get("source_revision", SOURCE_REVISION)}

    @task
    def enabled(settings, cloud):
        if cloud not in settings["clouds"]:
            raise AirflowSkipException(f"Ramo {cloud} não selecionado")
        return settings

    @task
    def bronze(settings, cloud):
        from utils import aws, azure
        from utils.config import read_config

        module = aws if cloud == "aws" else azure
        return checked(module.ingest, read_config()[cloud], settings["load_date"],
                       settings["revision"])

    @task
    def glue(bronze_result):
        from utils.aws import run_glue
        from utils.config import read_config

        return checked(run_glue, read_config()["aws"], bronze_result["load_date"])

    @task
    def transfer(result, cloud):
        from utils.config import read_config
        from utils.databricks import transfer_aws, transfer_azure

        function = transfer_aws if cloud == "aws" else transfer_azure
        return checked(function, read_config()[cloud], result)

    @task
    def databricks(transfer_result, cloud):
        from utils.config import read_config
        from utils.databricks import run_job

        return checked(run_job, read_config()["databricks"]["jobs"][cloud], transfer_result,
                       get_current_context()["run_id"])

    @task
    def athena(silver):
        from utils.aws import query_athena
        from utils.config import read_config

        return checked(query_athena, read_config()["aws"], silver)

    @task(trigger_rule="none_failed_min_one_success")
    def complete():
        print("Todos os ramos selecionados concluíram com sucesso.")

    settings = prepare()
    with TaskGroup("aws"):
        aws_bronze = bronze(enabled(settings, "aws"), "aws")
        silver = glue(aws_bronze)
        aws_gold = databricks(transfer(silver, "aws"), "aws")
        analytics = athena(silver)
    with TaskGroup("azure"):
        azure_bronze = bronze(enabled(settings, "azure"), "azure")
        azure_gold = databricks(transfer(azure_bronze, "azure"), "azure")
    [aws_gold, analytics, azure_gold] >> complete()


pipeline()
