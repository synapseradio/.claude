#!/usr/bin/env python3
"""Tests for the tag-indentation formatter under `scripts/format-rules-xml.py`.

Run with `python3.14 -m pytest scripts/tests/test_format_rules_xml.py`.

Every test but the last builds its own text and passes a path used only in
error messages, so no test writes to disk. The last test reads this
repository's own rules files and `CLAUDE.md` and writes nothing, so a rules
file that drifts out of the form fails here.
"""

import importlib.util
import pathlib
import re
import sys

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "scripts" / "format-rules-xml.py"

_spec = importlib.util.spec_from_file_location("format_rules_xml", SCRIPT_PATH)
assert _spec is not None and _spec.loader is not None
formatter = importlib.util.module_from_spec(_spec)
sys.modules["format_rules_xml"] = formatter
_spec.loader.exec_module(formatter)

PATH = pathlib.Path("rules/example.md")


def words(text: str) -> str:
    return re.sub(r"\s+", "", text)


class TestFrontmatter:
    def test_paths_frontmatter_passes_through_byte_for_byte(self):
        text = (
            "---\n"
            "paths:\n"
            '  - "**/*.{test,spec}.*"\n'
            '  - "**/{__tests__,__mocks__}/**"\n'
            "---\n"
            "\n"
            '<rule name="example">\n'
            "<applies_when>You are testing.</applies_when>\n"
            "</rule>\n"
        )
        result = formatter.format_text(text, PATH)
        assert result.startswith(
            '---\npaths:\n  - "**/*.{test,spec}.*"\n  - "**/{__tests__,__mocks__}/**"\n---\n'
        )

    def test_a_glob_brace_in_frontmatter_gains_no_backtick(self):
        text = (
            "---\n"
            "paths:\n"
            '  - "**/{.bashrc,.bash_profile}"\n'
            "---\n"
            "\n"
            '<rule name="example">\n'
            "<require>Never pass --no-verify.</require>\n"
            "</rule>\n"
        )
        assert '  - "**/{.bashrc,.bash_profile}"' in formatter.format_text(text, PATH)

    def test_a_file_without_frontmatter_gains_none(self):
        text = '<rule name="example">\n<require>Never guess.</require>\n</rule>\n'
        assert not formatter.format_text(text, PATH).startswith("---")


class TestIndentation:
    def test_an_element_indents_two_spaces_inside_its_parent(self):
        text = '<rule name="example">\n<require>\nNever guess.\n</require>\n</rule>\n'
        assert formatter.format_text(text, PATH) == (
            '<rule name="example">\n  <require>\n    Never guess.\n  </require>\n</rule>\n'
        )

    def test_prose_sharing_a_line_with_its_tags_moves_to_its_own_line(self):
        text = '<rule name="example">\n<applies_when>You are testing.</applies_when>\n</rule>\n'
        assert formatter.format_text(text, PATH) == (
            '<rule name="example">\n'
            "  <applies_when>\n"
            "    You are testing.\n"
            "  </applies_when>\n"
            "</rule>\n"
        )

    def test_a_nested_element_reaches_four_spaces(self):
        text = (
            '<rule name="example">\n'
            "<optimize_for>\n"
            "a suite that fails for one reason.\n"
            "<why_it_matters>A reason names itself.</why_it_matters>\n"
            "</optimize_for>\n"
            "</rule>\n"
        )
        assert formatter.format_text(text, PATH) == (
            '<rule name="example">\n'
            "  <optimize_for>\n"
            "    a suite that fails for one reason.\n"
            "    <why_it_matters>\n"
            "      A reason names itself.\n"
            "    </why_it_matters>\n"
            "  </optimize_for>\n"
            "</rule>\n"
        )

    def test_a_nested_list_item_keeps_its_indentation_relative_to_its_siblings(self):
        text = (
            '<rule name="example">\n'
            '<decide name="route">\n'
            "- A first arm.\n"
            "  - Its nested arm.\n"
            "- A second arm.\n"
            "</decide>\n"
            "</rule>\n"
        )
        assert formatter.format_text(text, PATH) == (
            '<rule name="example">\n'
            '  <decide name="route">\n'
            "    - A first arm.\n"
            "      - Its nested arm.\n"
            "    - A second arm.\n"
            "  </decide>\n"
            "</rule>\n"
        )

    def test_a_blank_line_between_siblings_survives_and_carries_no_spaces(self):
        text = '<rule name="example">\n\n<require>\nNever guess.\n</require>\n\n</rule>\n'
        result = formatter.format_text(text, PATH)
        assert "\n\n  <require>" in result
        assert not any(line.strip() == "" and line != "" for line in result.split("\n"))


class TestFencedBlocks:
    def test_a_fence_shifts_with_its_block_and_keeps_its_inner_layout(self):
        text = (
            '<rule name="example">\n'
            '<define name="prompt">\n'
            "Write the prompt in these parts.\n"
            "\n"
            "```xml\n"
            "<prompt>\n"
            "  <task>\n"
            "    [what to do]\n"
            "  </task>\n"
            "</prompt>\n"
            "```\n"
            "</define>\n"
            "</rule>\n"
        )
        assert formatter.format_text(text, PATH) == (
            '<rule name="example">\n'
            '  <define name="prompt">\n'
            "    Write the prompt in these parts.\n"
            "\n"
            "    ```xml\n"
            "    <prompt>\n"
            "      <task>\n"
            "        [what to do]\n"
            "      </task>\n"
            "    </prompt>\n"
            "    ```\n"
            "  </define>\n"
            "</rule>\n"
        )

    def test_a_tag_inside_a_fence_opens_no_element(self):
        text = '<rule name="example">\n<do>\n```xml\n<unclosed>\n```\n</do>\n</rule>\n'
        assert formatter.format_text(text, PATH).endswith("</rule>\n")

    def test_an_unclosed_fence_raises(self):
        text = '<rule name="example">\n<do>\n```xml\n<prompt>\n</do>\n</rule>\n'
        with pytest.raises(ValueError, match="fence never closes"):
            formatter.format_text(text, PATH)


class TestMalformedTags:
    def test_a_mismatched_close_names_both_tags_and_the_opening_line(self):
        text = '<rule name="example">\n<require>\nNever guess.\n</define>\n</rule>\n'
        with pytest.raises(ValueError, match=re.escape("</define> closes <require>")):
            formatter.format_text(text, PATH)

    def test_an_element_left_open_at_the_end_names_the_line_it_opened_on(self):
        text = '<rule name="example">\n<require>\nNever guess.\n'
        with pytest.raises(ValueError, match=re.escape("<require> opened at line 2")):
            formatter.format_text(text, PATH)

    def test_a_close_with_nothing_open_reports_that(self):
        text = "</require>\n"
        with pytest.raises(ValueError, match="closes nothing"):
            formatter.format_text(text, PATH)


class TestPreservation:
    def test_no_word_changes(self):
        text = (
            '<rule name="example">\n'
            "<applies_when>You are testing a `<subject>` in a heredoc, `<<'EOF'`.</applies_when>\n"
            "</rule>\n"
        )
        assert words(formatter.format_text(text, PATH)) == words(text)

    def test_a_second_pass_changes_nothing(self):
        text = (
            '<rule name="example">\n'
            "\n"
            '<decide name="route">\n'
            "- A first arm.\n"
            "  - Its nested arm.\n"
            "</decide>\n"
            "\n"
            "</rule>\n"
        )
        once = formatter.format_text(text, PATH)
        assert formatter.format_text(once, PATH) == once

    def test_a_file_carrying_no_rule_element_keeps_its_prose_flush_left(self):
        text = '---\npaths:\n  - "**/*.sh"\n---\n\n# Shell scripts\n\nThis applies when writing shell scripts.\n'
        result = formatter.format_text(text, PATH)
        assert "# Shell scripts" in result
        assert "  # Shell scripts" not in result


class TestOwnership:
    @pytest.mark.parametrize(
        "path",
        [
            "rules/testing.md",
            "rules/shell-scripts.md",
            "CLAUDE.md",
            "worktree/rules/git-commit.md",
        ],
    )
    def test_a_rules_file_or_claude_md_is_owned(self, path):
        assert formatter.owns(pathlib.Path(path))

    @pytest.mark.parametrize(
        "path",
        [
            "references/working-rules.md",
            "skills/waypoint/SKILL.md",
            "README.md",
            "agents/scout.md",
            "rules/testing.py",
        ],
    )
    def test_every_other_path_passes_through(self, path):
        assert not formatter.owns(pathlib.Path(path))


class TestThisRepository:
    """The rules files and CLAUDE.md of this checkout, path-scoped ones included."""

    def test_every_rules_file_and_claude_md_is_already_formatted(self):
        paths = [*sorted((REPO_ROOT / "rules").glob("*.md")), REPO_ROOT / "CLAUDE.md"]
        assert len(paths) > 1
        unformatted = [
            path.relative_to(REPO_ROOT).as_posix()
            for path in paths
            if formatter.format_text(path.read_text(encoding="utf-8"), path)
            != path.read_text(encoding="utf-8")
        ]
        assert unformatted == []
