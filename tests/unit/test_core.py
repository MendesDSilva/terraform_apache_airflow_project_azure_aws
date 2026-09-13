import io
import json
from unittest.mock import Mock

import pytest

from utils.config import bronze_path, load_date, validate_config
from utils.databricks import publish_files
from utils.ingestion import inspect_csv
from utils.polling import wait_terminal


@pytest.mark.parametrize("value", ["2025-02-30", "25-01-01", "../2025-01-01", None])
def test_bad_dates(value):
    with pytest.raises(ValueError):
        load_date(value)


def test_paths():
    assert bronze_path("2025-06-01", "bookings") == "load_date=2025-06-01/bookings/bookings.csv"
    with pytest.raises(ValueError):
        bronze_path("2025-06-01", "../other")


def test_csv_contract():
    valid = b"airport_id,airport_name,city,country\nA1,Airport,City,Country\n"
    assert inspect_csv(valid, "airports")["rows"] == 1
    for bad in [b"wrong\nvalue\n", valid.splitlines()[0], valid + b"A2,short\n"]:
        with pytest.raises(ValueError):
            inspect_csv(bad, "airports")


def test_missing_config_fails_before_cloud_call():
    with pytest.raises(ValueError, match="aws.bucket"):
        validate_config({}, "aws")


def test_polling_failure_and_timeout():
    with pytest.raises(RuntimeError, match="FAILED"):
        wait_terminal(lambda: "FAILED", lambda x: x, {"SUCCESS"}, {"FAILED"})
    with pytest.raises(TimeoutError):
        wait_terminal(lambda: "RUNNING", lambda x: x, {"SUCCESS"}, {"FAILED"}, timeout=0)
    assert wait_terminal(lambda: "SUCCESS", lambda x: x, {"SUCCESS"}, {"FAILED"}) == "SUCCESS"


def test_transfer_commits_only_after_verified_content():
    ws = Mock()
    ws.files.download.return_value.contents = io.BytesIO(b"data")
    result = publish_files(ws, "aws", "2025-06-01", [("part.parquet", b"data")])
    calls = ws.files.upload.call_args_list
    assert len(calls) == 2
    assert calls[-1].args[0] == result["path"] + "/manifest.json"
    assert json.loads(calls[-1].args[1].getvalue())["cloud"] == "aws"


def test_corruption_never_publishes_manifest():
    ws = Mock()
    ws.files.download.return_value.contents = io.BytesIO(b"corrupted")
    with pytest.raises(ValueError, match="Checksum"):
        publish_files(ws, "azure", "2025-06-01", [("bookings.csv", b"data")])
    assert ws.files.upload.call_count == 1
    assert not ws.files.upload.call_args.args[0].endswith("manifest.json")


def test_empty_transfer_never_commits():
    ws = Mock()
    with pytest.raises(ValueError, match="Nenhum"):
        publish_files(ws, "aws", "2025-06-01", [])
    ws.files.upload.assert_not_called()


def test_remote_upload_failure_never_commits():
    ws = Mock()
    ws.files.upload.side_effect = ConnectionError("network unavailable")
    with pytest.raises(ConnectionError):
        publish_files(ws, "aws", "2025-06-01", [("part.parquet", b"data")])
    assert ws.files.upload.call_count == 1
    ws.files.download.assert_not_called()
