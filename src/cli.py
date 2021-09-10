import logging
from pathlib import Path

import click

from src.bill import bill


@click.command(name="bill")
@click.argument("project", nargs=1)
def bill_cmd(project: str) -> None:
    bill(project=project)


if __name__ == "__main__":
    log_file = Path(f"{__file__}.log")
    log_format = "%(asctime)s:%(levelname)s:%(filename)s:%(lineno)d:%(message)s"
    logging.basicConfig(filename=log_file, level=logging.DEBUG, format=log_format)

    logging.info("Command started...")
    bill_cmd()
    logging.info("Finished command")
