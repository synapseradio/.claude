#!/usr/bin/env python3
"""Reading the pool tells every later step which rules exist and in which forms.

The reader serves the engineer writing composition, check, and render: they ask
the pool for a rule's default form and variants and for what each body claims in
its first line, and never walk `rules/` themselves. Each case builds its own
rulesets directory under `tmp_path`.

Run with `python3.14 -m pytest features/rulesets/tests/test_manifest_pool.py`.
"""

import pathlib
import sys

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]

sys.path.insert(0, str(PLUGIN_ROOT / "lib"))

from rulesets.source.pool import (  # noqa: E402  (path must be set before this import)
    FrontmatterCondition,
    Marker,
    read_pool,
)


def build(tmp_path, files):
    """A rulesets directory holding `files`, a mapping of relative path to text.

    A value of None makes a directory.
    """

    root = tmp_path / "rulesets"
    root.mkdir()
    for relative, text in files.items():
        target = root / relative
        if text is None:
            target.mkdir(parents=True)
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
    return root


class TestRuleNamesComeFromFileStems:
    def test_a_rule_holds_its_default_form_and_its_variants(self, tmp_path):
        root = build(
            tmp_path,
            {
                "rules/voice.md": "Speak plainly.\n",
                "rules/voice@terse.md": "Speak briefly.\n",
                "rules/voice@warm.md": "Speak kindly.\n",
            },
        )

        pool = read_pool(root)

        assert list(pool.rules) == ["voice"]
        voice = pool.rules["voice"]
        assert voice.default.text == "Speak plainly.\n"
        assert sorted(voice.variants) == ["terse", "warm"]
        assert voice.variants["terse"].text == "Speak briefly.\n"
        assert voice.variants["warm"].text == "Speak kindly.\n"

    def test_the_name_is_the_stem_up_to_the_first_at_sign(self, tmp_path):
        root = build(tmp_path, {"rules/a-b_c.md": "x", "rules/a-b_c@d-e.md": "y"})

        pool = read_pool(root)

        assert list(pool.rules) == ["a-b_c"]
        assert list(pool.rules["a-b_c"].variants) == ["d-e"]

    def test_rules_are_listed_by_name_whatever_order_the_files_were_written_in(self, tmp_path):
        root = build(
            tmp_path,
            {"rules/zeta.md": "z", "rules/alpha.md": "a", "rules/mid.md": "m"},
        )

        assert list(read_pool(root).rules) == ["alpha", "mid", "zeta"]

    def test_a_file_that_is_not_markdown_is_no_rule(self, tmp_path):
        root = build(tmp_path, {"rules/voice.md": "x", "rules/notes.txt": "y", "rules/.keep": ""})

        assert list(read_pool(root).rules) == ["voice"]

    def test_a_missing_pool_holds_no_rule(self, tmp_path):
        root = build(tmp_path, {"manifest.yaml": "defaults: []\n"})

        pool = read_pool(root)

        assert dict(pool.rules) == {}
        assert pool.stray_directories == ()

    def test_each_file_knows_its_path(self, tmp_path):
        root = build(tmp_path, {"rules/voice.md": "x", "rules/voice@terse.md": "y"})

        voice = read_pool(root).rules["voice"]

        assert voice.default.path == root / "rules" / "voice.md"
        assert voice.variants["terse"].path == root / "rules" / "voice@terse.md"


class TestAVariantNeedsNoDefaultToBeRead:
    def test_a_variant_beside_no_default_form_leaves_the_default_absent(self, tmp_path):
        root = build(tmp_path, {"rules/tone@dry.md": "Be dry.\n"})

        tone = read_pool(root).rules["tone"]

        assert tone.default is None
        assert list(tone.variants) == ["dry"]


class TestAnEmptyDefaultFormIsStillAForm:
    def test_an_empty_default_form_is_present_with_no_text(self, tmp_path):
        root = build(tmp_path, {"rules/voice.md": "", "rules/voice@terse.md": "Brief.\n"})

        voice = read_pool(root).rules["voice"]

        assert voice.default is not None
        assert voice.default.text == ""
        assert voice.variants["terse"].text == "Brief.\n"


class TestTheReservedReferencesFolder:
    def test_files_in_references_become_no_rule_and_no_variant(self, tmp_path):
        root = build(
            tmp_path,
            {
                "rules/voice.md": "x",
                "references/table.md": "a table",
                "references/extra@variant.md": "not a variant",
            },
        )

        pool = read_pool(root)

        assert list(pool.rules) == ["voice"]
        assert pool.rules["voice"].variants == {}

    def test_references_is_no_stray_directory(self, tmp_path):
        root = build(tmp_path, {"rules/voice.md": "x", "references/table.md": "a table"})

        assert read_pool(root).stray_directories == ()


class TestStrayDirectories:
    def test_a_directory_inside_the_pool_is_stray(self, tmp_path):
        root = build(tmp_path, {"rules/voice.md": "x", "rules/drafts/old.md": "y"})

        pool = read_pool(root)

        assert pool.stray_directories == (root / "rules" / "drafts",)
        assert list(pool.rules) == ["voice"]

    def test_a_directory_beside_the_pool_other_than_references_is_stray(self, tmp_path):
        root = build(tmp_path, {"rules/voice.md": "x", "renders": None, "references": None})

        assert read_pool(root).stray_directories == (root / "renders",)


class TestFirstLineMarkers:
    def test_a_default_form_marker_names_its_rule(self, tmp_path):
        root = build(tmp_path, {"rules/voice.md": "<!-- rule: voice -->\nSpeak.\n"})

        marker = read_pool(root).rules["voice"].default.marker

        assert marker == Marker(rule="voice", variant=None)

    def test_a_variant_marker_names_its_rule_and_variant(self, tmp_path):
        root = build(
            tmp_path,
            {
                "rules/voice.md": "x",
                "rules/voice@terse.md": "<!-- rule: voice variant: terse -->\nBrief.\n",
            },
        )

        marker = read_pool(root).rules["voice"].variants["terse"].marker

        assert marker == Marker(rule="voice", variant="terse")

    def test_a_body_with_no_marker_carries_none(self, tmp_path):
        root = build(tmp_path, {"rules/voice.md": "Speak.\n"})

        assert read_pool(root).rules["voice"].default.marker is None

    def test_a_marker_below_the_first_line_is_no_marker(self, tmp_path):
        root = build(tmp_path, {"rules/voice.md": "Speak.\n<!-- rule: voice -->\n"})

        assert read_pool(root).rules["voice"].default.marker is None

    def test_a_marker_naming_another_rule_is_read_as_written(self, tmp_path):
        root = build(tmp_path, {"rules/voice.md": "<!-- rule: sorting -->\nSpeak.\n"})

        marker = read_pool(root).rules["voice"].default.marker

        assert marker == Marker(rule="sorting", variant=None)

    def test_a_default_form_may_carry_the_marker_of_a_variant(self, tmp_path):
        root = build(tmp_path, {"rules/voice.md": "<!-- rule: voice variant: terse -->\n"})

        marker = read_pool(root).rules["voice"].default.marker

        assert marker == Marker(rule="voice", variant="terse")

    def test_a_line_of_prose_in_comment_syntax_is_no_marker(self, tmp_path):
        root = build(tmp_path, {"rules/voice.md": "<!-- rule: this and that -->\nSpeak.\n"})

        assert read_pool(root).rules["voice"].default.marker is None

    def test_a_file_that_opens_on_frontmatter_has_no_first_line_marker(self, tmp_path):
        root = build(
            tmp_path,
            {"rules/voice.md": "---\npaths: ['src/**']\n---\n<!-- rule: voice -->\nSpeak.\n"},
        )

        assert read_pool(root).rules["voice"].default.marker is None


class TestARuleIsUnconditionalText:
    def test_frontmatter_scoping_a_rule_to_paths_is_read_with_its_line(self, tmp_path):
        text = "---\ndescription: tone\npaths: ['src/**']\n---\nSpeak.\n"
        root = build(tmp_path, {"rules/voice.md": text})

        condition = read_pool(root).rules["voice"].default.condition

        assert condition == FrontmatterCondition(key="paths", line=3)

    def test_frontmatter_scoping_a_rule_to_a_model_is_read_with_its_line(self, tmp_path):
        root = build(tmp_path, {"rules/voice.md": "---\nmodel: haiku\n---\nSpeak.\n"})

        condition = read_pool(root).rules["voice"].default.condition

        assert condition == FrontmatterCondition(key="model", line=2)

    def test_frontmatter_that_scopes_nothing_carries_no_condition(self, tmp_path):
        root = build(tmp_path, {"rules/voice.md": "---\ndescription: tone\n---\nSpeak.\n"})

        assert read_pool(root).rules["voice"].default.condition is None

    def test_prose_describing_when_a_rule_applies_is_text_like_any_other(self, tmp_path):
        text = "On haiku models, keep answers short.\nOnly under paths: src/** apply this.\n"
        root = build(tmp_path, {"rules/voice.md": text})

        voice = read_pool(root).rules["voice"]

        assert voice.default.condition is None
        assert voice.default.text == text

    def test_frontmatter_that_does_not_parse_carries_no_condition(self, tmp_path):
        root = build(tmp_path, {"rules/voice.md": "---\npaths: [unclosed\n---\nSpeak.\n"})

        assert read_pool(root).rules["voice"].default.condition is None
