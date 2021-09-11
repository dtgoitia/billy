import logging
from pathlib import Path

import click

from src.bill import bill


@click.command(name="bill")
@click.argument("project", nargs=1)
@click.option(
    "--append-only",
    is_flag=True,
    help="Appends every time entry to the end of the existing table in GSheet",
)
@click.option(
    "--fetch-only",
    is_flag=True,
    help="Only fetch entries from Toggl, nothing else",
)
def bill_cmd(project: str, append_only: bool, fetch_only: bool) -> None:
    bill(project=project, append_only=append_only, fetch_only=fetch_only)


if __name__ == "__main__":
    log_file = Path(f"{__file__}.log")
    log_format = "%(asctime)s:%(levelname)s:%(filename)s:%(lineno)d:%(message)s"
    logging.basicConfig(filename=log_file, level=logging.DEBUG, format=log_format)

    logging.info("Command started...")
    bill_cmd()
    logging.info("Finished command")
