from __future__ import annotations

import datetime
import enum
from pathlib import Path
from typing import Dict, Iterator, List, Optional

import requests
from requests.auth import HTTPBasicAuth

from src.config import TogglApiToken, get_config
from src.types import (
    JsonDict,
    Project,
    ProjectAlias,
    TimeRange,
    TogglProjectId,
    TogglTimeEntry,
)

_CACHED_TOGGL_CLIENT: Optional[Toggl] = None
TOGGL_ENTRIES_CACHE = Path("~/toggl-cache.csv").expanduser()


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


#     def _get_entries_from_cache(
#         self,
#         time_range: Optional[TimeRange] = None,
#     ) -> Iterator[TogglTimeEntry]:
#         read_entries_from_cache(time_range=time_range)


# def read_entries_from_cache() -> List[TogglTimeEntry]:
#     # do not use a CSV, if you insert entries out of order.. you are fucked
#     # Use SQLite to filter by date
#     path = TOGGL_ENTRIES_CACHE
#     return entries


# def cache_entries(entries: List[TogglTimeEntry]) -> None:
#     for entry in entries:
#         entry

#     return entries


def get_toggl_client(token: TogglApiToken) -> Toggl:
    global _CACHED_TOGGL_CLIENT
    if _CACHED_TOGGL_CLIENT:
        return _CACHED_TOGGL_CLIENT

    client = Toggl(token=token)

    _CACHED_TOGGL_CLIENT = client

    return client


def _parse_toggl_entry(
    raw_entry: JsonDict,
    project_map: Dict[TogglProjectId, ProjectAlias],
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

    entry = TogglTimeEntry(
        id=raw_entry["id"],
        # wid=raw_entry["wid"],
        project=Project(id=project_id, alias=project_map.get(project_id)),
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

    # return [
    #     TogglTimeEntry(
    #         id=1,
    #         project=Project(id=174067391, alias="css"),
    #         start=datetime.datetime.fromisoformat("2013-03-11T11:36:00+00:00"),
    #         stop=datetime.datetime.fromisoformat("2013-03-11T11:38:00+00:00"),
    #         description="description 1",
    #     ),
    #     TogglTimeEntry(
    #         id=2,
    #         project=Project(id=174067391, alias="css"),
    #         start=datetime.datetime.fromisoformat("2013-03-11T11:38:00+00:00"),
    #         stop=datetime.datetime.fromisoformat("2013-03-11T11:39:00+00:00"),
    #         description="description 2",
    #     ),
    # ]
