from __future__ import annotations

import datetime
from typing import Dict, Iterator, List, Optional, Union

import gspread
from gspread import Client as GSheetClient
from gspread.models import Spreadsheet, Worksheet

from src.config import get_config
from src.types import ProjectAlias, ProjectDailyStats

_CACHED_GSHEET_CLIENT: Optional[GSheetClient] = None
MIN_DATE = datetime.date.min

GSheetCell = Union[str, bool, int]
GSheetRow = List[GSheetCell]


def get_sheet_client() -> GSheetClient:
    global _CACHED_GSHEET_CLIENT
    if _CACHED_GSHEET_CLIENT:
        return _CACHED_GSHEET_CLIENT

    client = gspread.oauth()

    _CACHED_GSHEET_CLIENT = client

    return client


def stats_to_cells(stats: ProjectDailyStats) -> Iterator[GSheetRow]:
    """Return cells: date, description, seconds, billable"""
    date_str = stats.date.isoformat()
    for entry in stats.entries:
        row: GSheetRow = [date_str, entry.description, entry.duration, entry.billable]
        yield row


WorksheetName = str
WorksheetIndex = int
WorksheetIndexToMap = Dict[WorksheetName, Worksheet]


def get_sheets_name_to_index_map(spreadsheet: Spreadsheet) -> WorksheetIndexToMap:
    return {sheet.title: index for index, sheet in enumerate(spreadsheet)}


def delete_rows_with_last_date(sheet: Worksheet) -> datetime.date:
    """Delete rows from the bottom up, and returns deleted date value"""
    first_column = sheet.col_values(1)  # columns start counting at 1
    bottom_row_value = first_column[-1]
    try:
        last_date = datetime.date.fromisoformat(bottom_row_value)
    except ValueError:
        # no date found in bottom_row_value, hence return early not to delete anything
        # and return the earliest day possible so that no entries are skipped
        return datetime.date.min

    start_index = first_column.index(bottom_row_value) + 1
    end_index = len(first_column)

    sheet.delete_rows(start_index=start_index, end_index=end_index)

    return last_date


def upload_to_gsheet(stats: List[ProjectDailyStats], append_only: bool) -> None:
    client = get_sheet_client()
    config = get_config()

    spreadsheet = client.open_by_url(config.gsheet_url)
    name_to_index = get_sheets_name_to_index_map(spreadsheet)

    sorted_stats = sorted(stats, key=lambda s: s.date)

    checked_projects: Dict[ProjectAlias, datetime.date] = {}

    for project_stats in sorted_stats:
        alias = project_stats.alias

        # Get worksheet
        if alias not in name_to_index:
            # TODO: create sheet automatically
            raise NotImplementedError("create sheet manually for the time being")
        worksheet_index = name_to_index[alias]
        sheet = spreadsheet.get_worksheet(worksheet_index)

        # Delete all entries from the last recorded day, as it might be partially
        # uploaded, and reupload that day and any following days
        must_delete_rows_with_last_date = (
            alias not in checked_projects and append_only is False
        )
        if append_only is True and alias not in checked_projects:
            checked_projects[alias] = MIN_DATE
        if must_delete_rows_with_last_date:
            removed_date = delete_rows_with_last_date(sheet)
            print(f"Deleted {removed_date} entries for {alias!r}")
            checked_projects[alias] = removed_date
        else:
            removed_date = checked_projects[alias]

        # skip all stats before the last removed date
        if project_stats.date < removed_date:
            print(f"Skipping {project_stats.date} for {alias!r}")
            continue

        new_rows = list(stats_to_cells(project_stats))

        print(f"Appending {project_stats.date} for {alias!r}")
        sheet.append_rows(new_rows)
