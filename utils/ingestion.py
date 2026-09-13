"""Download limitado e validação de contrato antes de publicar Bronze."""
import csv
import hashlib
import io

from utils.config import DATASETS, SOURCE_REVISION

HEADERS = {
    "bookings": ["booking_id", "passenger_id", "flight_id", "airport_id", "amount", "booking_date"],
    "passengers": ["passenger_id", "name", "gender", "nationality"],
    "airports": ["airport_id", "airport_name", "city", "country"],
}
MAX_BYTES = 20 * 1024 * 1024


def checksum(data):
    return hashlib.sha256(data).hexdigest()


def inspect_csv(data, dataset):
    reader = csv.DictReader(io.StringIO(data.decode("utf-8-sig")))
    if reader.fieldnames != HEADERS[dataset]:
        raise ValueError(f"Schema inesperado: {dataset}")
    count = 0
    for row in reader:
        if None in row or None in row.values():
            raise ValueError(f"Linha CSV malformada: {dataset}")
        count += 1
    if count == 0:
        raise ValueError(f"CSV vazio: {dataset}")
    return {"dataset": dataset, "rows": count, "bytes": len(data), "sha256": checksum(data)}


def download(dataset, revision=SOURCE_REVISION):
    import requests

    if dataset not in DATASETS:
        raise ValueError("Dataset desconhecido")
    url = f"https://raw.githubusercontent.com/anshlambagit/ApacheAirflow/{revision}/{dataset}.csv"
    with requests.get(url, timeout=(10, 60), stream=True) as response:
        response.raise_for_status()
        data = bytearray()
        for chunk in response.iter_content(65536):
            data.extend(chunk)
            if len(data) > MAX_BYTES:
                raise ValueError("CSV ultrapassou limite didático de 20 MiB")
    data = bytes(data)
    return data, inspect_csv(data, dataset)
