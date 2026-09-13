# Databricks notebook source
# common.py é concatenado a este notebook pelo Terraform para não depender de sys.path.
day = valid_day(dbutils.widgets.get("load_date"))
path = dbutils.widgets.get("input_path")
names = verify_manifest(spark, path, "aws", day)
silver = spark.read.parquet(*[path + "/" + name for name in names])
if not silver.limit(1).count() or silver.filter(
    F.col("load_date").isNull() | (F.col("load_date") != day)
).limit(1).count():
    raise ValueError("Silver AWS vazia ou com carga incorreta")
write_snapshot(silver, "`aws-airflow-gold`.silver.bookings_enriched", day)
