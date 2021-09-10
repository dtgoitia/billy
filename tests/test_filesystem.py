import json

from src.filesystem import remove_comments_from_json


def test_parse_json_with_comments():
    json_with_comments = (
        "// Comment 1\n"
        "{\n"
        "    // Comment 2\n"
        '    "url": "https://example.com/",\n'
        '    "foo": 1234  // Comment 3\n'
        "}  // Comment 4\n"
        "// Comment 5\n"
        "//Comment 6\n"
    )

    valid_json_str = remove_comments_from_json(json_with_comments)
    content = json.loads(valid_json_str)
    assert content == {
        "url": "https://example.com/",
        "foo": 1234,
    }
