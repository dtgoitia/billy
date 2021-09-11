import datetime
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

from src.filesystem import abort_if_file_does_not_exist, read_json_with_comments
from src.types import JsonDict, Project, TogglProjectId

DOTFILES_DIR = Path("~/.config/billy").expanduser()
CONFIG_PATH = DOTFILES_DIR / "config.jsonc"
CREDENTIALS_PATH = DOTFILES_DIR / "credentials.jsonc"

logger = logging.getLogger(__name__)

TogglApiToken = str


@dataclass
class AppConfig:
    projects: List[Project]
    toggl_api_token: TogglApiToken
    gsheet_url: str

    @property
    def project_id_to_name_map(self) -> Dict[TogglProjectId, Project]:
        return {project.id: project for project in self.projects}


def abort_if_config_file_does_not_exist(path: Path) -> None:
    msg = f"Please create config file at: {path}"
    abort_if_file_does_not_exist(path=path, message=msg)


def abort_if_credentials_file_does_not_exist(path: Path) -> None:
    msg = f"Please create credentials file at: {path}"
    abort_if_file_does_not_exist(path=path, message=msg)


def parse_project(raw: JsonDict) -> Project:
    """
    {
      "id": 1234,
      "alias": "project alias",
      "start": "2021-01-01"
    }
    """
    isoformat = f'{raw["start"]}T00:00:00+00:00'  # make it tz aware
    project = Project(
        id=raw["id"],
        alias=raw["alias"],
        start_date=datetime.datetime.fromisoformat(isoformat),
    )
    return project


def parse_config(config_path: Path, credentials_path: Path) -> AppConfig:
    raw_config = read_json_with_comments(path=CONFIG_PATH)
    projects = list(map(parse_project, raw_config["projects"]))

    credentials = read_json_with_comments(path=credentials_path)
    api_token: TogglApiToken = credentials["toggle_api_token"]
    gsheet_url = credentials["gsheet_url"]

    config = AppConfig(
        projects=projects,
        toggl_api_token=api_token,
        gsheet_url=gsheet_url,
    )
    return config


_CACHED_APP_CONFIG: Optional[AppConfig] = None


def get_config() -> AppConfig:
    global _CACHED_APP_CONFIG
    if _CACHED_APP_CONFIG:
        return _CACHED_APP_CONFIG

    abort_if_config_file_does_not_exist(path=CONFIG_PATH)
    abort_if_credentials_file_does_not_exist(path=CREDENTIALS_PATH)

    config = parse_config(config_path=CONFIG_PATH, credentials_path=CREDENTIALS_PATH)

    _CACHED_APP_CONFIG = config

    return config
