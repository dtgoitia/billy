from __future__ import annotations

import datetime
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

JsonDict = Dict[str, Any]
TogglEntryId = int
TogglProjectId = int
ProjectAlias = Optional[str]
TogglEntryDescription = str
DurationInSeconds = int


@dataclass
class Project:
    id: TogglProjectId
    alias: ProjectAlias


@dataclass
class TogglTimeEntry:
    id: TogglEntryId
    project: Project
    description: TogglEntryDescription
    start: datetime.datetime
    stop: Optional[datetime.datetime] = None

    @property
    def ongoing(self) -> bool:
        return self.stop is None

    def delta(self) -> Optional[datetime.timedelta]:
        if self.ongoing or self.stop is None:
            return None

        return self.stop - self.start

    def duration(self) -> Optional[DurationInSeconds]:
        if delta := self.delta():
            return round(delta.total_seconds())

        return None


@dataclass
class TimeRange:
    after: datetime.datetime
    before: datetime.datetime


@dataclass
class DailyStat:
    date: datetime.date
    entries: List[EntrySummary]


@dataclass
class ProjectDailyStats:
    alias: ProjectAlias
    date: datetime.date
    entries: List[EntrySummary]


@dataclass
class EntrySummary:
    description: TogglEntryDescription
    duration: DurationInSeconds

    @property
    def billable(self) -> bool:
        return "(no charge)" not in self.description
