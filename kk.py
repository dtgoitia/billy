import csv
import itertools
import time
from pathlib import Path
from typing import Iterator, List

from src.types import JsonDict

FILE_NAME = "big_sample.csv"


def kk():
    import sqlite3

    db = sqlite3.connect(":memory:")
    breakpoint()


def create_sample_data() -> Iterator[JsonDict]:
    amount = 300_000
    for i in range(amount):
        item = {
            "id": i,
            "project_id": 123,
            "project_alias": "foo",
            "start": "2013-03-11T11:36:00+00:00",
            "stop": "2013-03-11T15:36:00+00:00",
            "description": "Meeting with the client",
        }
        yield item


def create_sample_csv():
    path = Path(FILE_NAME)  # ~27MB
    items = create_sample_data()
    first_item = next(items)
    with path.open("w") as f:
        headers = [k for k in first_item.keys()]
        writer = csv.DictWriter(f, fieldnames=headers)

        writer.writeheader()

        for item in itertools.chain([first_item], items):
            writer.writerow(item)


def read_sample_csv() -> Iterator[JsonDict]:
    path = Path(FILE_NAME)  # ~27MB
    with path.open("r") as f:
        reader = csv.DictReader(f)

        for item in reader:
            yield item


def read_sample_data():
    data = list(read_sample_csv())
    print(len(data))


start = time.time()
read_sample_data()
delta = time.time() - start
print(delta)
