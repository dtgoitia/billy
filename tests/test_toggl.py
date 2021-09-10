import datetime
from typing import List

import pytest

from src.toggl import TOGGL_ENTRIES_CACHE, cache_entries, read_cache
from src.types import Project, TimeRange, TogglTimeEntry


def generate_sample_data() -> List[TogglTimeEntry]:
    years = 8
    entries_per_day = 20
    amount = years * (365 * entries_per_day)

    entries = []
    start = datetime.datetime(2021, 1, 1)
    delta = datetime.timedelta(seconds=1000)
    stop_delta = delta + datetime.timedelta(seconds=4)
    for i in range(amount):
        entry = TogglTimeEntry(
            id=i,
            project=Project(
                id=1,
                alias="foo",
                start_date=datetime.datetime(2021, 2, 1),
            ),
            description="description",
            start=start,
            stop=start + stop_delta,
        )
        entries.append(entry)
        start += stop_delta + delta
    return entries


@pytest.mark.skip(reason="ony for development purposes")
def test_cache():
    entries = generate_sample_data()

    TOGGL_ENTRIES_CACHE.unlink()
    cache_entries(entries)

    rg = TimeRange(
        after=datetime.datetime(2021, 1, 13),
        until=datetime.datetime(2021, 1, 16),
    )
    for i, entry in enumerate(read_cache(rg)):
        print(i, entry)
