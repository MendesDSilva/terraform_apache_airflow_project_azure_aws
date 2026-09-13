# Databricks notebook source
day = valid_day(dbutils.widgets.get("load_date"))
path = dbutils.widgets.get("input_path")
verify_manifest(spark, path, "azure", day)
frames = [read_csv(spark, f"{path}/{name}.csv", name)
          for name in ("bookings", "passengers", "airports")]
silver = build_silver(*frames, day)
write_snapshot(silver, "`azure-airflow-gold`.silver.bookings_enriched", day)
