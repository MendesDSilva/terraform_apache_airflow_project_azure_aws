from pathlib import Path

from airflow.dag_processing.dagbag import DagBag


def test_dag_import_and_topology():
    root = Path(__file__).resolve().parents[2]
    bag = DagBag(dag_folder=str(root / "dags"))
    assert bag.import_errors == {}
    dag = bag.dags["multi_cloud_data_pipeline"]
    assert dag.max_active_runs == 1
    assert "aws.glue" in dag.task_ids
    assert "azure.databricks" in dag.task_ids
    assert dag.get_task("aws.glue").downstream_task_ids == {"aws.transfer", "aws.athena"}
    assert dag.get_task("complete").upstream_task_ids == {
        "aws.databricks", "azure.databricks", "aws.athena"}
    assert dag.get_task("complete").trigger_rule.value == "none_failed_min_one_success"
