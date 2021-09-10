import json
import logging
import re
import sys
from pathlib import Path

from src.types import JsonDict

logger = logging.getLogger(__name__)


def read_json_with_comments(path: Path) -> JsonDict:
    json_with_comments = path.read_text()
    json_str = remove_comments_from_json(json_with_comments)
    content = json.loads(json_str)

    return content


# match any "//" that is not in an URL
HAS_JS_COMMENT = re.compile(r"(^|[^:])\/\/[^a-zA-Z0-9]?")
COMMENT_AT_BEGINNING_OF_LINE = re.compile(r"^//")


def remove_comments_from_json(content: str) -> str:
    clean_lines = []
    for line in content.split("\n"):
        has_comment = HAS_JS_COMMENT.search(line)
        if has_comment:
            clean_line = line.strip()
            if COMMENT_AT_BEGINNING_OF_LINE.match(clean_line):
                # The whole line is a comment, skip it
                continue
            else:
                # Remove the comment and anything in the line after the comment
                clean_line = line
                position_of_comment = clean_line.index("//")
                clean_line = clean_line[:position_of_comment].strip()
        else:
            clean_line = line
        clean_lines.append(clean_line)

    json_str = "\n".join(clean_lines)
    return json_str


def abort_if_file_does_not_exist(path: Path, message: str) -> None:
    if path.exists():
        return

    logger.error(message)
    print(message)
    sys.exit(1)
