from __future__ import annotations

from typing import Dict, Iterator, List, Optional, Union

import gspread
from gspread import Client as GSheetClient
from gspread.models import Spreadsheet, Worksheet

from src.config import get_config
from src.types import ProjectDailyStats

_CACHED_GSHEET_CLIENT: Optional[GSheetClient] = None

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


def upload_to_gsheet(stats: List[ProjectDailyStats]) -> None:
    client = get_sheet_client()
    config = get_config()

    spreadsheet = client.open_by_url(config.gsheet_url)
    name_to_index = get_sheets_name_to_index_map(spreadsheet)

    for project_stats in stats:
        alias = project_stats.alias
        if alias not in name_to_index:
            # TODO: create sheet automatically
            raise NotImplementedError("create sheet manually for the time being")
        worksheet_index = name_to_index[alias]
        new_rows = list(stats_to_cells(project_stats))

        sheet = spreadsheet.get_worksheet(worksheet_index)
        sheet.append_rows(new_rows)
