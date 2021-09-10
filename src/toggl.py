from __future__ import annotations

import datetime
import enum
from pathlib import Path
from typing import Dict, Iterator, List, Optional, Union, cast

import requests
from requests.auth import HTTPBasicAuth

from src.config import TogglApiToken, get_config
from src.types import JsonDict, Project, TimeRange, TogglProjectId, TogglTimeEntry

_CACHED_TOGGL_CLIENT: Optional[Toggl] = None


class Endpoint(enum.Enum):
    TIME_ENTRIES = "https://api.track.toggl.com/api/v8/time_entries"


# from toggl.TogglPy import Toggl


class Toggl:  # TODO: rename to TogglClient
    _token: TogglApiToken

    def __init__(self, token: TogglApiToken) -> None:
        self._token = token

    def _get(self, endpoint: str) -> List[JsonDict]:
        result = requests.get(endpoint, auth=HTTPBasicAuth(self._token, "api_token"))
        result.raise_for_status()
        return result.json()

    def get_entries(self, tr: Optional[TimeRange] = None) -> Iterator[TogglTimeEntry]:
        data = self._get("https://api.track.toggl.com/api/v8/time_entries")
        project_map = get_config().project_id_to_name_map
        for raw_time_entry in data:
            entry = _parse_toggl_entry(raw_time_entry, project_map)
            yield entry


def get_toggl_client(token: TogglApiToken) -> Toggl:
    global _CACHED_TOGGL_CLIENT
    if _CACHED_TOGGL_CLIENT:
        return _CACHED_TOGGL_CLIENT

    client = Toggl(token=token)

    _CACHED_TOGGL_CLIENT = client

    return client


def _parse_toggl_entry(
    raw_entry: JsonDict,
    project_map: Dict[TogglProjectId, Project],
) -> TogglTimeEntry:
    """
    {
        "id":436691234,
        "wid":777,
        "pid":123,
        "billable":true,
        "start":"2013-03-11T11:36:00+00:00",
        "stop":"2013-03-11T15:36:00+00:00",
        "duration":14400,
        "description":"Meeting with the client",
        "tags":[""],
        "at":"2013-03-11T15:36:58+00:00"
    }
    """
    project_id: TogglProjectId = raw_entry["pid"]

    stop: Optional[datetime.datetime] = None
    if "stop" in raw_entry:
        stop = datetime.datetime.fromisoformat(raw_entry["stop"])

    if project_id in project_map:
        project = project_map[project_id]
    else:
        min_date = datetime.datetime.min
        project = Project(id=raw_entry["pid"], alias="", start_date=min_date)

    entry = TogglTimeEntry(
        id=raw_entry["id"],
        # wid=raw_entry["wid"],
        project=project,
        # billable=raw_entry["billable"],
        start=datetime.datetime.fromisoformat(raw_entry["start"]),
        stop=stop,
        # duration=raw_entry["duration"],
        description=raw_entry["description"],
        # tags=raw_entry["tags"],
        # at=raw_entry["at"],
    )
    return entry


def get_project_entries(
    *,
    pid: TogglProjectId,
    time_range: Optional[TimeRange] = None,
) -> Iterator[TogglTimeEntry]:

    # The API doesn't filter entries per project. It forces you to fetch all entries and
    # then filter them locally
    # TODO: cache them locally to avoid calling too much
    config = get_config()
    toggl = get_toggl_client(token=config.toggl_api_token)
    time_entries = toggl.get_entries()
    for entry in time_entries:
        if entry.project.id == pid:
            yield entry


# ======================================================================================
# CAVEAT: this is a bad hack to get it working ASAP, you should use a DB...
#
# Use SQLite to filter by date, etc.

import csv  # noqa

TOGGL_ENTRIES_CACHE = Path("toggl-cache.csv")
# TODO: once you remove this hack, remove the cache file from the .gitignore

CacheKey = str
TableRow = List[Union[str, int]]


def build_key(entry: TogglTimeEntry) -> CacheKey:
    # return f"{entry.description}{CACHE_KEY_DELIMITER}{ts}"
    ts = entry.start.isoformat()
    return ts


def entry_to_table_row(entry: TogglTimeEntry) -> TableRow:
    return [
        entry.id,
        entry.project.id,
        entry.project.alias or "NO_ALIAS",
        entry.project.start_date.isoformat(),
        entry.description,
        entry.start.isoformat(),
        entry.stop.isoformat(),  # type:ignore
    ]


def table_row_to_entry(row: TableRow) -> TogglTimeEntry:
    return TogglTimeEntry(
        id=cast(int, row[0]),
        project=Project(
            id=cast(int, row[1]),
            alias=cast(str, row[2]),
            start_date=datetime.datetime.fromisoformat(cast(str, row[3])),
        ),
        description=cast(str, row[4]),
        start=datetime.datetime.fromisoformat(cast(str, row[5])),
        stop=datetime.datetime.fromisoformat(cast(str, row[6])),
    )


def read_cache(time_range: Optional[TimeRange] = None) -> Iterator[TogglTimeEntry]:
    entries_iter = load_cache()
    if time_range is None:
        yield from entries_iter
        return

    for entry in entries_iter:
        if entry.start < time_range.after:
            continue

        if time_range.after <= entry.start:
            if time_range.until is None:
                yield entry
                continue

            if entry.stop <= time_range.until:  # type: ignore
                yield entry
                continue

        if time_range.until and time_range.until < entry.stop:  # type: ignore
            break


def load_cache() -> Iterator[TogglTimeEntry]:
    # Assumption: all entries are sorted by start date
    with TOGGL_ENTRIES_CACHE.open("r") as f:
        for row in csv.reader(f):
            entry = table_row_to_entry(row)  # type: ignore
            yield entry


def cache_entries(entries: List[TogglTimeEntry]) -> None:
    # Assumption: all entries must be sorted by start date
    with TOGGL_ENTRIES_CACHE.open("a") as f:
        writer = csv.writer(f)
        for entry in entries:
            row = entry_to_table_row(entry)
            writer.writerow(row)


# Test that they are appended
