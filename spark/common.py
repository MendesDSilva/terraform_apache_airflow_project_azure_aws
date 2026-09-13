"""Contratos reais dos CSVs e transformações portáveis em Spark SQL."""
import json
import re
from datetime import date

from pyspark.sql import functions as F
from pyspark.sql.types import StringType, StructField, StructType

FIELDS = {
    "bookings": "booking_id passenger_id flight_id airport_id amount booking_date".split(),
    "passengers": "passenger_id name gender nationality".split(),
    "airports": "airport_id airport_name city country".split(),
}


def valid_day(day):
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", day):
        raise ValueError("Data inválida")
    return date.fromisoformat(day).isoformat()


def read_csv(spark, path, dataset):
    # enforceSchema=false também verifica o cabeçalho, evitando casts por posição errada.
    schema = StructType([StructField(name, StringType(), True) for name in FIELDS[dataset]])
    return (spark.read.option("header", True).option("mode", "FAILFAST")
            .option("enforceSchema", False).schema(schema).csv(path))


def clean_dimension(df, key):
    df = df.select([F.when(F.trim(F.col(c)) == "", None).otherwise(
        F.trim(F.col(c))).alias(c) for c in df.columns]).dropDuplicates()
    if df.filter(F.col(key).isNull()).limit(1).count():
        raise ValueError(f"Chave obrigatória ausente: {key}")
    if df.groupBy(key).count().filter("count > 1").limit(1).count():
        raise ValueError(f"Valores conflitantes para chave: {key}")
    return df


def build_silver(bookings, passengers, airports, day):
    day = valid_day(day)
    bookings = clean_dimension(bookings, "booking_id")
    passengers = clean_dimension(passengers, "passenger_id")
    airports = clean_dimension(airports, "airport_id")
    # try_cast torna o erro de contrato previsível em runtimes com ANSI habilitado.
    bookings = bookings.withColumn("amount", F.expr("try_cast(amount as decimal(18,2))"))
    bookings = bookings.withColumn("booking_date", F.expr("try_cast(booking_date as date)"))
    required = ["passenger_id", "flight_id", "airport_id", "amount", "booking_date"]
    invalid = F.lit(False)
    for column in required:
        invalid = invalid | F.col(column).isNull()
    if bookings.filter(invalid | (F.col("amount") < 0)).limit(1).count():
        raise ValueError("Reserva com campo obrigatório inválido ou valor negativo")
    if not bookings.limit(1).count():
        raise ValueError("Reservas vazias")
    passengers = passengers.withColumn("passenger_found", F.lit(True))
    airports = airports.withColumn("airport_found", F.lit(True))
    result = (bookings.join(passengers, "passenger_id", "left")
              .join(airports, "airport_id", "left")
              .fillna(False, subset=["passenger_found", "airport_found"])
              .withColumn("load_date", F.lit(day).cast("date")))
    counts = result.agg(F.count("*").alias("rows"),
                        F.sum((~F.col("passenger_found")).cast("int")).alias("missing_passengers"),
                        F.sum((~F.col("airport_found")).cast("int")).alias("missing_airports"))
    print("silver_quality=" + json.dumps(counts.first().asDict()))
    return result


def build_gold(silver):
    return silver.groupBy("load_date", "booking_date", "airport_id", "airport_name",
                          "city", "country").agg(
        F.count("*").alias("total_bookings"),
        F.countDistinct("passenger_id").alias("distinct_passengers"),
        F.countDistinct("flight_id").alias("distinct_flights"),
        F.sum("amount").alias("total_amount"),
        F.avg("amount").cast("decimal(18,2)").alias("average_amount"))


def write_snapshot(df, table, day):
    day = valid_day(day)
    # Um único commit Delta substitui a carga; outras datas permanecem intactas.
    (df.write.format("delta").mode("overwrite")
     .option("replaceWhere", f"load_date = '{day}'").saveAsTable(table))


def verify_manifest(spark, path, cloud, day):
    import hashlib

    expected = f"/Volumes/{cloud}-airflow-gold/staging/inbound/load_date={valid_day(day)}/"
    if not path.startswith(expected) or not re.fullmatch(r"[0-9a-f]{32}", path[len(expected):]):
        raise ValueError("Caminho de entrada fora do volume/carga esperados")
    # Spark binaryFile funciona também no serverless sem depender de DBFS root/FUSE.
    rows = spark.read.format("binaryFile").load(path + "/manifest.json").collect()
    manifest = json.loads(bytes(rows[0].content))
    if manifest["cloud"] != cloud or manifest["load_date"] != day or not manifest["files"]:
        raise ValueError("Manifesto incompatível com o job")
    names = [item["name"] for item in manifest["files"]]
    if len(set(names)) != len(names) or any("/" in name or name in (".", "..") for name in names):
        raise ValueError("Nomes inválidos no manifesto")
    if cloud == "azure" and set(names) != {name + ".csv" for name in FIELDS}:
        raise ValueError("Manifesto Azure deve conter os três CSVs")
    for item in manifest["files"]:
        row = spark.read.format("binaryFile").load(path + "/" + item["name"]).first()
        content = bytes(row.content)
        if len(content) != item["bytes"] or hashlib.sha256(content).hexdigest() != item["sha256"]:
            raise ValueError("Arquivo incompleto ou alterado após transferência")
    return names
