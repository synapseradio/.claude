#!/usr/bin/env python3
"""One splitter decides where a markdown file's frontmatter block begins and ends.

The renderer reading a rule body, the pool reader scoping a rule file, and the agent
definition reader all open a file the same way, so a file ending its block with no trailing
newline, with Windows line endings, or with spaces after the fence reads as having
frontmatter in all of them or in none. Each case builds its text inline.

Run with `python3.14 -m pytest features/plugins/rulesets/tests/test_documents.py`.
"""

import pathlib
import sys

import pytest

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]

sys.path.insert(0, str(PLUGIN_ROOT / "lib"))

from rulesets.documents import parse_document, split_frontmatter  # noqa: E402

FENCE_VARIANTS = {
    "a newline after the closing fence": "---\nname: scout\n---\nBody\n",
    "no newline after the closing fence": "---\nname: scout\n---",
    "Windows line endings": "---\r\nname: scout\r\n---\r\nBody\r\n",
    "spaces after both fences": "---  \nname: scout\n---  \nBody\n",
}


class TestSplitFrontmatter:
    def test_the_block_comes_back_with_the_file_line_it_opens_on(self):
        assert split_frontmatter("---\nname: scout\nmodel: haiku\n---\nBody\n") == (
            "name: scout\nmodel: haiku",
            2,
        )

    @pytest.mark.parametrize("text", FENCE_VARIANTS.values(), ids=FENCE_VARIANTS.keys())
    def test_a_fence_written_four_ways_yields_the_same_block(self, text):
        assert split_frontmatter(text) == ("name: scout", 2)

    def test_a_block_between_adjacent_fences_is_empty(self):
        assert split_frontmatter("---\n---\nBody\n") == ("", 2)

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
    def test_a_file_without_a_closed_block_at_its_first_line_has_none(self, text):
        assert split_frontmatter(text) is None


class TestParseDocument:
    @pytest.mark.parametrize("text", FENCE_VARIANTS.values(), ids=FENCE_VARIANTS.keys())
    def test_a_fence_written_four_ways_parses_the_same_frontmatter(self, text):
        assert parse_document(text).frontmatter == {"name": "scout"}

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
    def test_the_body_is_what_follows_the_closing_fence_without_the_blank_separator(
        self, text, body
    ):
        assert parse_document(text).body == body

    def test_a_file_without_a_block_is_all_body(self):
        text = "Some prose\n\n---\n\nmore prose\n"

        document = parse_document(text)

        assert (document.frontmatter, document.body) == (None, text)

    @pytest.mark.parametrize("text", ["---\n\n---\nBody\n", "---\n---\nBody\n"])
    def test_a_block_that_holds_nothing_is_an_empty_mapping(self, text):
        assert parse_document(text).frontmatter == {}
