# Databricks notebook source
day = valid_day(dbutils.widgets.get("load_date"))
cloud = dbutils.widgets.get("cloud")
if cloud not in ("aws", "azure"):
    raise ValueError("Cloud inválida")
catalog = f"`{cloud}-airflow-gold`"
silver = spark.table(f"{catalog}.silver.bookings_enriched").filter(F.col("load_date") == day)
gold = build_gold(silver)
if not gold.limit(1).count():
    raise ValueError("Gold vazia")
write_snapshot(gold, f"{catalog}.gold.bookings_daily_airport", day)
print("gold_rows=", gold.count())
