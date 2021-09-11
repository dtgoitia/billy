from __future__ import annotations

import datetime
import enum
from pathlib import Path
from typing import Dict, Iterator, List, Optional, Tuple, Union, cast

import requests
from requests.auth import HTTPBasicAuth

from src.config import TogglApiToken, get_config
from src.types import JsonDict, Project, TimeRange, TogglProjectId, TogglTimeEntry

_CACHED_TOGGL_CLIENT: Optional[Toggl] = None


class Endpoint(enum.Enum):
    TIME_ENTRIES = "https://api.track.toggl.com/api/v8/time_entries"


class ProjectNotSupported(Exception):
    # This mainly will happen when you try to parse an Toggl entry which belongs to a
    # project that is not specified in the config
    ...


class Toggl:  # TODO: rename to TogglClient
    _token: TogglApiToken

    def __init__(self, token: TogglApiToken) -> None:
        self._token = token

    def _get(self, endpoint: str, params: Dict) -> List[JsonDict]:
        result = requests.get(
            endpoint,
            auth=HTTPBasicAuth(self._token, "api_token"),
            params=params,
        )
        result.raise_for_status()
        return result.json()

    def get_entries(self, tr: Optional[TimeRange] = None) -> Iterator[TogglTimeEntry]:
        # https://github.com/toggl/toggl_api_docs/blob/master/chapters/time_entries.md
        updated_tr, cached_entries = find_cached_entries(tr)
        i = 0
        for i, cached_entry in enumerate(cached_entries):
            yield cached_entry

        print(f"{i} entries from cache...")

        if updated_tr is None:
            # Case when the cache has been deleted, only query from the earliest project
            # date in the config, nothing more
            config = get_config()
            earliest_date = sorted(proj.start_date for proj in config.projects)[0]
            updated_tr = TimeRange(after=earliest_date)

        params = {"start_date": updated_tr.after.isoformat()}
        if updated_tr.until:
            params["end_date"] = updated_tr.until.isoformat()

        data = self._get("https://api.track.toggl.com/api/v8/time_entries", params)
        project_map = get_config().project_id_to_name_map
        entries_to_cache = []
        for raw_time_entry in data:
            try:
                entry = _parse_toggl_entry(raw_time_entry, project_map)
            except ProjectNotSupported:
                # Toggl returns entries for all projects. It doesn't allow filtering per
                # project. However, that doesn't mean you need to cache entries from
                # projects you don't care about.
                # pro: you save space in caching and reduce load/write time
                # con: when adding a new project, you need to remove cache and fetch all
                #      entries again - which is fine because it occurs very rarely
                continue
            entries_to_cache.append(entry)
            yield entry

        cache_entries(entries_to_cache)


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
        raise ProjectNotSupported

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
    time_entries = toggl.get_entries(tr=time_range)
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


def find_cached_entries(
    tr: Optional[TimeRange],
) -> Tuple[Optional[TimeRange], List[TogglTimeEntry]]:
    """Most common use case: find all entries from a given time on."""
    cached_entries = list(read_cache(tr))
    if not cached_entries:
        return tr, []

    last_datetime = cached_entries[-1].start  # TODO: should this be start or stop?
    last_datetime += datetime.timedelta(seconds=1)
    updated_tr = TimeRange(after=last_datetime, until=tr.until if tr else None)
    return updated_tr, cached_entries


def entry_to_table_row(entry: TogglTimeEntry) -> TableRow:
    return [
        entry.id,
        entry.project.id,
        entry.project.alias,
        entry.project.start_date.isoformat(),
        entry.description,
        entry.start.isoformat(),
        entry.stop.isoformat(),  # type:ignore
    ]


def table_row_to_entry(row: TableRow) -> TogglTimeEntry:
    return TogglTimeEntry(
        id=int(row[0]),
        project=Project(
            id=int(row[1]),
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
    if TOGGL_ENTRIES_CACHE.exists() is False:
        return

    with TOGGL_ENTRIES_CACHE.open("r") as f:
        for row in csv.reader(f):
            entry = table_row_to_entry(row)  # type: ignore
            yield entry


def cache_entries(entries: List[TogglTimeEntry]) -> None:
    # Assumption: all entries must be sorted by start date
    with TOGGL_ENTRIES_CACHE.open("a") as f:
        writer = csv.writer(f)
        for entry in entries:
            if entry.stop is None:
                # Ongoing time entry, just ignore it
                continue
            row = entry_to_table_row(entry)
            writer.writerow(row)


def remove_cache() -> None:
    if not TOGGL_ENTRIES_CACHE.exists():
        return

    TOGGL_ENTRIES_CACHE.unlink()
