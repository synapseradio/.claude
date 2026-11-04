#!/usr/bin/env python3
"""Parsing the manifest keeps the file line of everything a check error must point at.

The parser serves the engineer writing check, explain, and composition: each key, ruleset
declaration, `when` item, and reference arrives with its line, a file that does not parse
is told apart from one that parses into the wrong shape, and a missing manifest reads as
the default every pool rule gets. Each case writes its manifest under `tmp_path`.

Run with `python3.14 -m pytest features/plugins/model-scoped-rulesets/tests/test_manifest_parse.py`.
"""

import pathlib
import sys

import pytest

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]

sys.path.insert(0, str(PLUGIN_ROOT / "lib"))

from rulesets.source import manifest  # noqa: E402  (path must be set before this import)
from rulesets.source.manifest import (  # noqa: E402
    MalformedItem,
    ReservedRulesetDeclared,
    UnknownKey,
    UnquotedModel,
    WrongKeyShape,
    WrongRulesetShape,
)

SITUATION_ONE = """\
models: ['opus', 'sonnet', 'haiku', 'fable', 'opus-4-8']
defaults: ['all:*', '-security-pass', '-review-method']
rulesets:
  code: ['writing-code', 'data-modeling']
  reviewer: ['review-method', 'report-format']
when:
  - model haiku: ['-code:*']
  - agent critic and not model haiku: ['reviewer:*']
  - agent critic and flag strict: ['security-pass']
  - flag voice-terse: ['voice@terse']
"""

PATH = pathlib.Path("manifest.yaml")


def parse(text):
    return manifest.parse_manifest(text, PATH)


def texts(references):
    return [reference.text for reference in references]


def lines(references):
    return [reference.line for reference in references]


class TestTheFourKeys:
    def test_models_come_back_as_written(self):
        assert parse(SITUATION_ONE).models == ("opus", "sonnet", "haiku", "fable", "opus-4-8")

    def test_defaults_come_back_as_references_with_their_lines(self):
        defaults = parse(SITUATION_ONE).defaults

        assert texts(defaults.references) == ["all:*", "-security-pass", "-review-method"]
        assert lines(defaults.references) == [2, 2, 2]

    def test_each_ruleset_comes_back_with_its_declaration_line_and_references(self):
        rulesets = parse(SITUATION_ONE).rulesets

        assert list(rulesets) == ["code", "reviewer"]
        assert (rulesets["code"].name, rulesets["code"].line) == ("code", 4)
        assert texts(rulesets["code"].references) == ["writing-code", "data-modeling"]
        assert (rulesets["reviewer"].name, rulesets["reviewer"].line) == ("reviewer", 5)
        assert texts(rulesets["reviewer"].references) == ["review-method", "report-format"]

    def test_each_when_item_comes_back_with_its_index_line_condition_and_references(self):
        items = parse(SITUATION_ONE).items

        assert [(item.index, item.line, item.condition) for item in items] == [
            (0, 7, "model haiku"),
            (1, 8, "agent critic and not model haiku"),
            (2, 9, "agent critic and flag strict"),
            (3, 10, "flag voice-terse"),
        ]
        assert [texts(item.references) for item in items] == [
            ["-code:*"],
            ["reviewer:*"],
            ["security-pass"],
            ["voice@terse"],
        ]
        assert [lines(item.references) for item in items] == [[7], [8], [9], [10]]

    def test_a_key_of_the_wrong_shape_is_named_with_the_line_of_the_key(self):
        text = "# the models\nmodels: opus\n\ndefaults: x\nrulesets: []\nwhen: {}\n"

        assert parse(text).problems == (
            WrongKeyShape("models", 2),
            WrongKeyShape("defaults", 4),
            WrongKeyShape("rulesets", 5),
            WrongKeyShape("when", 6),
        )

    def test_a_valid_manifest_holds_no_problem(self):
        assert parse(SITUATION_ONE).problems == ()


class TestEachReferenceKeepsItsOwnLine:
    def test_references_in_a_block_list_sit_on_their_own_lines(self):
        text = "defaults:\n  - 'all:*'\n  - '-security-pass'\n  - 'voice@terse'\n"

        assert lines(parse(text).defaults.references) == [2, 3, 4]

    def test_references_in_a_block_list_inside_a_ruleset_and_an_item(self):
        text = (
            "rulesets:\n"
            "  code:\n"
            "    - 'writing-code'\n"
            "    - 'data-modeling'\n"
            "when:\n"
            "  - flag strict:\n"
            "      - 'security-pass'\n"
            "      - '-voice'\n"
        )
        parsed = parse(text)

        assert lines(parsed.rulesets["code"].references) == [3, 4]
        assert (parsed.rulesets["code"].line, parsed.items[0].line) == (2, 6)
        assert lines(parsed.items[0].references) == [7, 8]

    def test_a_reference_is_read_as_written_even_where_yaml_would_read_a_number(self):
        parsed = parse("defaults: ['2024', 'quoted']\n")

        assert texts(parsed.defaults.references) == ["2024", "quoted"]


class TestAMissingOrEmptyManifest:
    def test_a_missing_manifest_reads_as_defaults_spreading_every_pool_rule(self, tmp_path):
        parsed = manifest.read_manifest(tmp_path)

        assert texts(parsed.defaults.references) == ["all:*"]
        assert parsed.models == ()
        assert dict(parsed.rulesets) == {}
        assert parsed.items == ()
        assert parsed.problems == ()

    def test_a_manifest_that_exists_is_read_from_its_file(self, tmp_path):
        (tmp_path / "manifest.yaml").write_text("defaults: ['voice']\n", encoding="utf-8")

        parsed = manifest.read_manifest(tmp_path)

        assert texts(parsed.defaults.references) == ["voice"]
        assert parsed.path == tmp_path / "manifest.yaml"

    def test_an_empty_manifest_holds_nothing_rather_than_every_rule(self, tmp_path):
        (tmp_path / "manifest.yaml").write_text("# nothing yet\n", encoding="utf-8")

        parsed = manifest.read_manifest(tmp_path)

        assert parsed.defaults is None
        assert parsed.models == ()
        assert dict(parsed.rulesets) == {}
        assert parsed.items == ()
        assert parsed.problems == ()

    def test_a_missing_key_holds_nothing(self):
        parsed = parse("models: ['opus']\n")

        assert parsed.defaults is None
        assert dict(parsed.rulesets) == {}
        assert parsed.items == ()


class TestAParseFailureIsNotAShapeError:
    def test_an_unquoted_model_name_holding_brackets_fails_to_parse(self):
        with pytest.raises(manifest.ManifestParseError) as failure:
            parse("models: [opus, opus-4-8[1m]]\n")

        assert failure.value.path == PATH
        assert failure.value.line == 1

    def test_the_failure_names_the_file_and_line_in_its_message(self):
        with pytest.raises(manifest.ManifestParseError) as failure:
            parse("defaults: []\nmodels: [opus, opus-4-8[1m]]\n")

        assert str(failure.value).startswith("manifest.yaml:2: ")

    def test_the_quoted_name_parses(self):
        parsed = parse('models: ["opus", "opus-4-8[1m]"]\n')

        assert parsed.models == ("opus", "opus-4-8[1m]")

    def test_the_block_form_parses(self):
        parsed = parse("models:\n  - 'opus'\n  - 'opus-4-8[1m]'\n")

        assert parsed.models == ("opus", "opus-4-8[1m]")

    def test_a_document_that_is_no_mapping_fails_to_parse(self):
        with pytest.raises(manifest.ManifestParseError):
            parse("- defaults\n- models\n")

    def test_read_manifest_raises_for_a_file_that_does_not_parse(self, tmp_path):
        (tmp_path / "manifest.yaml").write_text("defaults: [a\n", encoding="utf-8")

        with pytest.raises(manifest.ManifestParseError) as failure:
            manifest.read_manifest(tmp_path)

        assert failure.value.path == tmp_path / "manifest.yaml"

    def test_a_wrong_shape_parses_into_a_manifest_and_names_its_problem(self):
        parsed = parse("defaults:\n  all: true\n")

        assert parsed.problems == (WrongKeyShape("defaults", 1),)


class TestAWrongShapeLeavesTheRestOfTheManifestStanding:
    def test_a_top_level_key_nobody_defines_is_ignored_and_named(self):
        parsed = parse("defaults: ['voice']\nproject: amboss\n")

        assert texts(parsed.defaults.references) == ["voice"]
        assert parsed.problems == (UnknownKey("project", 2),)

    def test_an_unquoted_model_entry_is_skipped_and_named(self):
        parsed = parse("models: [opus, 'sonnet', 5, {a: b}]\n")

        assert parsed.models == ("sonnet",)
        assert parsed.problems == (
            UnquotedModel("opus", 1, "plain"),
            UnquotedModel("5", 1, "plain"),
            UnquotedModel("{a: b}", 1, "mapping"),
        )

    def test_models_that_is_not_a_list_holds_nothing(self):
        for text in ("models: opus\n", "models: {opus: 1}\n"):
            parsed = parse(text)

            assert parsed.models == ()
            assert parsed.problems == (WrongKeyShape("models", 1),)

    def test_defaults_that_is_not_a_list_holds_nothing(self):
        parsed = parse("defaults: all:*\nmodels: ['opus']\n")

        assert parsed.defaults is None
        assert parsed.models == ("opus",)
        assert parsed.problems == (WrongKeyShape("defaults", 1),)

    def test_rulesets_that_is_not_a_mapping_holds_nothing(self):
        parsed = parse("rulesets: [code]\n")

        assert dict(parsed.rulesets) == {}
        assert parsed.problems == (WrongKeyShape("rulesets", 1),)

    def test_when_that_is_not_a_list_holds_nothing(self):
        parsed = parse("when:\n  flag strict: [voice]\n")

        assert parsed.items == ()
        assert parsed.problems == (WrongKeyShape("when", 1),)

    def test_a_ruleset_whose_value_is_not_a_list_is_declared_and_holds_nothing(self):
        parsed = parse("rulesets:\n  code: {a: b}\n  tone: ['voice']\n")

        assert parsed.rulesets["code"].references == ()
        assert parsed.rulesets["code"].line == 2
        assert texts(parsed.rulesets["tone"].references) == ["voice"]
        assert parsed.problems == (WrongRulesetShape("code", 2),)

    def test_a_reserved_ruleset_declaration_is_skipped_and_named(self):
        parsed = parse("rulesets:\n  all: ['voice']\n  none: []\n  tone: ['voice']\n")

        assert list(parsed.rulesets) == ["tone"]
        assert parsed.problems == (
            ReservedRulesetDeclared("all", 2),
            ReservedRulesetDeclared("none", 3),
        )

    def test_a_ruleset_named_defaults_or_rules_is_reserved_too(self):
        parsed = parse("rulesets:\n  defaults: ['voice']\n  rules: ['voice']\n")

        assert dict(parsed.rulesets) == {}
        assert parsed.problems == (
            ReservedRulesetDeclared("defaults", 2),
            ReservedRulesetDeclared("rules", 3),
        )

    def test_a_when_item_that_is_no_one_key_mapping_to_a_list_is_skipped_and_named(self):
        text = (
            "when:\n"
            "  - flag a: ['voice']\n"
            "  - just a string\n"
            "  - {flag b: [voice], flag c: [voice]}\n"
            "  - flag d: {x: y}\n"
            "  - flag e: ['voice']\n"
        )
        parsed = parse(text)

        assert [(item.index, item.condition) for item in parsed.items] == [
            (0, "flag a"),
            (4, "flag e"),
        ]
        assert parsed.problems == (MalformedItem(1, 3), MalformedItem(2, 4), MalformedItem(3, 5))

    def test_the_manifest_keeps_the_path_it_was_read_from(self):
        parsed = manifest.parse_manifest("project: x\n", pathlib.Path("/pool/manifest.yaml"))

        assert parsed.path == pathlib.Path("/pool/manifest.yaml")

    def test_one_model_name_declared_twice_is_no_problem(self):
        parsed = parse("models: ['sonnet', 'sonnet']\n")

        assert parsed.problems == ()
