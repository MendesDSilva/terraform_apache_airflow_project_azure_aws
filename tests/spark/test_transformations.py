from decimal import Decimal

import pytest
from delta import configure_spark_with_delta_pip
from pyspark.sql import SparkSession

from spark.common import FIELDS, build_gold, build_silver, write_snapshot


@pytest.fixture(scope="module")
def session(tmp_path_factory):
    root = tmp_path_factory.mktemp("warehouse")
    builder = (SparkSession.builder.master("local[2]").appName("multicloud-tests")
               .config("spark.sql.shuffle.partitions", "2")
               .config("spark.sql.warehouse.dir", str(root))
               .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension")
               .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog"))
    spark = configure_spark_with_delta_pip(builder).getOrCreate()
    yield spark
    spark.stop()


def frames(spark, conflict=False):
    rows = [("B1", "P1", "F1", "A1", "10.50", "2025-06-01"),
            ("B1", "P1", "F1", "A1", "10.50", "2025-06-01"),
            ("B2", "P2", "F1", "A1", "20.50", "2025-06-01")]
    if conflict:
        rows.append(("B1", "P1", "F1", "A1", "99.00", "2025-06-01"))
    return (spark.createDataFrame(rows, FIELDS["bookings"]),
            spark.createDataFrame([("P1", "Person", "X", "BR")], FIELDS["passengers"]),
            spark.createDataFrame([("A1", "Airport", "City", "BR")], FIELDS["airports"]))


def test_join_and_metrics(session):
    silver = build_silver(*frames(session), "2025-06-02")
    assert silver.count() == 2
    assert silver.filter("not passenger_found").count() == 1
    row = build_gold(silver).first()
    assert row.total_bookings == 2
    assert row.distinct_passengers == 2
    assert row.distinct_flights == 1
    assert row.total_amount == Decimal("31.00")
    assert row.average_amount == Decimal("15.50")


def test_conflicting_keys_fail(session):
    with pytest.raises(ValueError, match="conflitantes"):
        build_silver(*frames(session, conflict=True), "2025-06-02")


def test_delta_rerun_preserves_other_days(session):
    table = "default.test_snapshot"
    first = build_gold(build_silver(*frames(session), "2025-06-02"))
    second = build_gold(build_silver(*frames(session), "2025-06-03"))
    write_snapshot(first, table, "2025-06-02")
    write_snapshot(second, table, "2025-06-03")
    write_snapshot(first, table, "2025-06-02")
    assert session.table(table).count() == 2
    assert session.table(table).filter("load_date = '2025-06-02'").first().total_bookings == 2


def test_invalid_amount_fails(session):
    from pyspark.sql import functions as F

    bookings, passengers, airports = frames(session)
    bookings = bookings.withColumn("amount", F.lit("invalid"))
    with pytest.raises(ValueError, match="obrigatório"):
        build_silver(bookings, passengers, airports, "2025-06-02")


def test_parquet_bridge_has_same_gold(session, tmp_path):
    direct = build_silver(*frames(session), "2025-06-02")
    target = str(tmp_path / "silver")
    direct.write.parquet(target)
    copied = session.read.parquet(target)
    assert build_gold(direct).collect() == build_gold(copied).collect()
