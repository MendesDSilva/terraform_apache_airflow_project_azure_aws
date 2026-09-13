"""Entrypoint Glue; common.py é distribuído via --extra-py-files."""
import sys

from awsglue.utils import getResolvedOptions
from common import build_silver, read_csv, valid_day
from pyspark.sql import SparkSession

args = getResolvedOptions(sys.argv, ["bucket", "load_date", "output_path"])
spark = SparkSession.builder.getOrCreate()
day = valid_day(args["load_date"])
base = f"s3://{args['bucket']}/bronze/load_date={day}"
frames = [read_csv(spark, f"{base}/{name}/{name}.csv", name)
          for name in ("bookings", "passengers", "airports")]
silver = build_silver(*frames, day)
silver.coalesce(1).write.mode("overwrite").parquet(args["output_path"])
