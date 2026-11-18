#!/usr/bin/env python3
"""One splitter decides where a markdown file's frontmatter block begins and ends.

The renderer reading a rule body, the pool reader scoping a rule file, and the agent
definition reader all open a file the same way, so a file ending its block with no trailing
newline, with Windows line endings, or with spaces after the fence reads as having
frontmatter in all of them or in none. Each case builds its text inline.

Run with `python3.15 -m pytest features/plugins/rulesets/tests/test_documents.py`.
"""

import pytest
from rulesets.documents import parse_document


@pytest.mark.parametrize(
    ("text", "body"),
    [
        ("---\nname: scout\n---\nBody\n", "Body\n"),
        ("---\nname: scout\n---", ""),
        ("---\r\nname: scout\r\n---\r\n\r\nBody\r\n", "Body\r\n"),
        ("---  \nname: scout\n---  \n\nBody\n", "Body\n"),
    ],
    ids=["newline", "no newline", "Windows line endings", "spaces"],
)
def test_a_fence_written_four_ways_yields_the_same_frontmatter_and_the_body_after_it(
    text, body
) -> None:
    document = parse_document(text)

    assert document.frontmatter == {"name": "scout"}
    assert document.body == body


@pytest.mark.parametrize(
    "text",
    [
        "",
        "Some prose\n\n---\n\nmore prose\n",
        "---\nname: scout\nno closing fence\n",
        "---only a heading rule",
    ],
    ids=["empty", "fence mid-file", "unclosed", "text after the dashes"],
)
def test_a_file_without_a_closed_block_at_its_first_line_is_all_body(text) -> None:
    document = parse_document(text)

    assert (document.frontmatter, document.body) == (None, text)
