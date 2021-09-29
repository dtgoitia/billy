from __future__ import annotations

import datetime
from typing import Dict, Iterator, List, Optional, Tuple, Union

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

    config = get_config()
    client = gspread.oauth(
        credentials_filename=config.gspread_credentials_path,
        authorized_user_filename=config.gspread_authorized_user_path,
    )
    if client.auth.expired:
        print("Deleting expired Google Spreadsheet credentials...")
        config.gspread_authorized_user_path.unlink()

        client = gspread.oauth(
            credentials_filename=config.gspread_credentials_path,
            authorized_user_filename=config.gspread_authorized_user_path,
        )

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


RowIndex = int  # 0-based index
RowNumber = int  # 1-based index
ColumnIndex = int  # 0-based index
ColumnNumber = int  # 1-based index


def row_index_to_number(index: RowIndex) -> RowNumber:
    number = index + 1
    return number


def column_index_to_number(index: ColumnIndex) -> ColumnNumber:
    number = index + 1
    return number


def column_name_to_number(name: str) -> int:
    """Map column name to column number - columns start counting at 1"""
    chars = [
        "A",
        "B",
        "C",
        "D",
        "E",
        "F",
        "G",
        "H",
        "I",
        "J",
        "K",
        "L",
        "M",
        "N",
        "O",
        "P",
        "Q",
        "R",
        "S",
        "T",
        "U",
        "V",
        "W",
        "X",
        "Z",
    ]
    column_index = chars.index(name)
    column_number = column_index + 1
    return column_number


def find_last_date(sheet: Worksheet) -> datetime.date:
    first_column = sheet.col_values(column_name_to_number("A"))
    bottom_row_value = first_column[-1]
    try:
        last_date = datetime.date.fromisoformat(bottom_row_value)
    except ValueError:
        # no date found in bottom_row_value, hence return early not to delete anything
        # and return the earliest day possible so that no entries are skipped
        return datetime.date.min

    return last_date


def find_last_date_rows_range(sheet: Worksheet) -> Tuple[RowNumber, RowNumber]:
    first_column = sheet.col_values(column_name_to_number("A"))
    bottom_row_value = first_column[-1]

    start_index: RowIndex = first_column.index(bottom_row_value)
    start = row_index_to_number(start_index)

    end: RowNumber = len(first_column)

    return start, end


def check_if_last_row_invoiced(sheet: Worksheet) -> bool:
    """Return True if the last row in the sheet has an invoiced entry

    An invoiced entry must have any value in column I.

    Assumption: days are invoiced in full - either all the entries in a given day are
    invoiced or none are invoiced, but a day cannot be partially invoiced.
    """
    start_row_number, _ = find_last_date_rows_range(sheet)

    invoices_column_number = column_name_to_number("I")
    invoices_column = sheet.col_values(invoices_column_number)
    last_invoiced_row: RowNumber = len(invoices_column)

    last_row_was_invoiced = start_row_number <= last_invoiced_row

    return last_row_was_invoiced


def delete_rows_with_last_date(sheet: Worksheet) -> datetime.date:
    """Delete rows from the bottom up, and returns deleted date value"""
    last_date = find_last_date(sheet)  # Store last date before deleting any rows

    start_number, end_number = find_last_date_rows_range(sheet)
    sheet.delete_rows(start_index=start_number, end_index=end_number)

    return last_date


def upload_to_gsheet(stats: List[ProjectDailyStats], append_only: bool) -> None:
    client = get_sheet_client()
    config = get_config()

    spreadsheet = client.open_by_url(config.gsheet_url)
    name_to_index = get_sheets_name_to_index_map(spreadsheet)

    sorted_stats = sorted(stats, key=lambda s: s.date)

    # "checked": a project is "checked" if the program has already inspected the GSheet
    # tab of the project and deleted the last row/entry in that tab.
    #
    # Each stat specifies the Toggl project it belongs to, but the stats list is not
    # sorted per project, which means that if you don't track if you have already
    # "checked" a project or not, you might end up deleting the "last" row multiple
    # times (aka, you delete mulitple bottom lines when you should only delete the last
    # one).
    checked_projects: Dict[ProjectAlias, datetime.date] = {}
    invoiced_per_project: Dict[ProjectAlias, bool] = {}

    for project_stats in sorted_stats:
        alias = project_stats.alias

        # Get worksheet
        if alias not in name_to_index:
            # TODO: create sheet automatically
            raise NotImplementedError("create sheet manually for the time being")
        worksheet_index = name_to_index[alias]
        sheet = spreadsheet.get_worksheet(worksheet_index)

        # Check if the last recorded entry has already been invoiced
        last_invoiced_row_already_inspected = alias in invoiced_per_project
        if not append_only and not last_invoiced_row_already_inspected:
            last_row_was_invoiced = check_if_last_row_invoiced(sheet)
            invoiced_per_project[alias] = last_row_was_invoiced
        else:
            last_row_was_invoiced = invoiced_per_project[alias]

        # Delete all entries from the last recorded day, as it might be partially
        # uploaded, and reupload that day and any following days
        # Do not delete if last recorded day was already invoiced
        must_delete_rows_with_last_date = (
            alias not in checked_projects and append_only is False
        )
        if append_only is True and alias not in checked_projects:
            checked_projects[alias] = MIN_DATE
        if must_delete_rows_with_last_date:
            if last_row_was_invoiced:
                # do not delete last date rows, just append after the last date
                last_date = find_last_date(sheet)
                cut_date = last_date + datetime.timedelta(days=1)
            else:
                cut_date = delete_rows_with_last_date(sheet)
                print(f"Deleted {cut_date} entries for {alias!r}")
            checked_projects[alias] = cut_date
        else:
            cut_date = checked_projects[alias]

        if project_stats.date < cut_date:
            print(f"Skipping {project_stats.date} for {alias!r}")
            continue

        new_rows = list(stats_to_cells(project_stats))

        print(f"Appending {project_stats.date} for {alias!r}")
        sheet.append_rows(new_rows)
