import datetime

from src.bill import aggregate_entries
from src.types import EntrySummary, Project, ProjectDailyStats, TogglTimeEntry


def test_aggregate_entries_per_project_per_day_and_per_description():
    any_date = datetime.datetime.now()
    do_foo_1 = TogglTimeEntry(
        id=1001,
        project=Project(1234, alias="project alias 1", start_date=any_date),
        start=datetime.datetime.fromisoformat("2013-03-11T11:36:00+00:00"),
        stop=datetime.datetime.fromisoformat("2013-03-11T11:38:00+00:00"),
        description="do foo",
    )
    do_bar = TogglTimeEntry(
        id=1002,
        project=Project(1234, alias="project alias 1", start_date=any_date),
        start=datetime.datetime.fromisoformat("2013-03-11T11:36:00+00:00"),
        stop=datetime.datetime.fromisoformat("2013-03-11T11:38:00+00:00"),
        description="do bar",
    )
    do_foo_2 = TogglTimeEntry(
        id=1003,
        project=Project(1234, alias="project alias 1", start_date=any_date),
        start=datetime.datetime.fromisoformat("2013-03-11T11:38:00+00:00"),
        stop=datetime.datetime.fromisoformat("2013-03-11T11:48:00+00:00"),
        description="do foo",
    )
    entries = [do_foo_1, do_bar, do_foo_2]

    daily_stats = aggregate_entries(entries)

    assert daily_stats == [
        ProjectDailyStats(
            date=datetime.date.fromisoformat("2013-03-11"),
            alias="project alias 1",
            entries=[
                EntrySummary(description="do foo", duration=720),
                EntrySummary(description="do bar", duration=120),
            ],
        ),
    ]
