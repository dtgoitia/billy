import datetime
from typing import Dict, List, Optional, Tuple

from src import toggl
from src.config import get_config
from src.gsheet import upload_to_gsheet
from src.types import (
    DurationInSeconds,
    EntrySummary,
    ProjectAlias,
    ProjectDailyStats,
    TimeRange,
    TogglEntryDescription,
    TogglProjectId,
    TogglTimeEntry,
)


def bill(
    project: ProjectAlias,
    clean_cache: bool,
    fetch_only: bool,
    append_only: bool,
    after: Optional[datetime.datetime] = None,
    until: Optional[datetime.datetime] = None,
) -> None:
    if clean_cache is True:
        print("Deleting cache file...", end="")
        toggl.remove_cache()
        print(" done!")

    toggl_project_id = get_toggl_project_id(alias=project)

    if after is None:
        earliest_date = get_project_earliest_date(project)
        after = earliest_date

    range = TimeRange(after=after, until=until)

    entries = list(toggl.get_project_entries(pid=toggl_project_id, time_range=range))
    print(f"Entries fetched: {len(entries)}")
    stats = aggregate_entries(entries)
    print(f"Stats: {len(stats)}")

    if fetch_only:
        return

    print("Updating GSheet")
    upload_to_gsheet(stats, append_only=append_only)


def get_project_earliest_date(alias: ProjectAlias) -> datetime.datetime:
    config = get_config()
    project = next(project for project in config.projects if project.alias == alias)
    return project.start_date


def get_toggl_project_id(alias: ProjectAlias) -> TogglProjectId:
    config = get_config()
    for project in config.projects:
        if project.alias == alias:
            return project.id
    else:
        raise ProjectAliasNotFound(f"Alias {alias!r} not found in config")


class ProjectAliasNotFound(Exception):
    ...


def aggregate_entries(entries: List[TogglTimeEntry]) -> List[ProjectDailyStats]:
    # Aggregate entries per project, day and task description
    # TODO: make this in a single loop

    """
    {
        ("css", "2021-01-01", "General"): 111,
        ("css", "2021-01-01", "Meeting"): 222,
        ("hiru", "2021-01-02", "General"): 333,
        ("hiru", "2021-01-02", "Meeting"): 444,
    }
    """
    duration_aggregation: Dict[
        Tuple[ProjectAlias, datetime.date, TogglEntryDescription],
        DurationInSeconds,
    ] = {}
    for entry in entries:
        duration = entry.duration()
        if duration is None:
            # Ongoing task, ignore it
            continue

        key = (entry.project.alias, entry.start.date(), entry.description)
        if key in duration_aggregation:
            duration_aggregation[key] += duration
        else:
            duration_aggregation[key] = duration

    """
    {
        ("css", "2021-01-01"): {
            "General": 111,
            "Meeting": 222,
        },
        ("hiru", "2021-01-02"): {
            "General": 333,
            "Meeting": 444,
        },
    }
    """
    aggregation: Dict[
        Tuple[ProjectAlias, datetime.date],
        Dict[TogglEntryDescription, DurationInSeconds],
    ] = {}
    for (alias, date, description), duration in duration_aggregation.items():
        _key = (alias, date)
        if _key in aggregation:
            aggregation[_key][description] = duration
        else:
            aggregation[_key] = {description: duration}

    project_daily_stats = []
    for (alias, date), entry_summary in aggregation.items():
        _entries = [
            EntrySummary(description=description, duration=duration)
            for description, duration in entry_summary.items()
        ]
        pds = ProjectDailyStats(alias=alias, date=date, entries=_entries)
        project_daily_stats.append(pds)

    return project_daily_stats
