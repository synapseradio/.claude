#!/usr/bin/env python3
"""Parsing the config keeps the file line of every word a check error must point at.

The parser serves the engineer writing check, explain, and composition: each key, set
declaration, block, and reference arrives with its line; a nested block and a `then` list
arrive as blocks of their own under their combined condition; a file that does not parse is
told apart from one that parses into the wrong shape; and a missing config reads as the
default every pool rule gets. Each case writes its config under `tmp_path`.

Run with `python3.15 -m pytest features/plugins/rulesets/tests/test_config_parse.py`.
"""

import pathlib
import sys

import pytest

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]

sys.path.insert(0, str(PLUGIN_ROOT / "lib"))

from rulesets.check.run import check  # noqa: E402  (path must be set before this import)
from rulesets.compose.composition import compose  # noqa: E402
from rulesets.facts.context import ABSENT, Facts  # noqa: E402
from rulesets.session.state import SessionState  # noqa: E402
from rulesets.source import config  # noqa: E402
from rulesets.source.config import (  # noqa: E402
    Config,
    DottedRulesetName,
    DuplicateKey,
    OldLayoutKey,
    ReservedRulesetDeclared,
    WrongBlockShape,
    WrongKeyShape,
    WrongListShape,
    WrongRulesetShape,
)
from rulesets.source.directory import read_directory  # noqa: E402

SITUATION_ONE = """\
models: opus sonnet haiku fable opus-4-8
defaults:
  include: all.*
  exclude: security-pass review-method
sets:
  code: writing-code data-modeling
  reviewer: review-method report-format
model haiku:
  exclude: code.*
agent critic:
  not model haiku:
    include: reviewer.*
  flag strict:
    include: security-pass
flag voice-terse:
  include: voice@terse
"""

PATH = pathlib.Path("config.yaml")


def parse(text) -> Config:
    return config.parse_config(text, PATH)


def texts(references) -> list[str]:
    return [reference.text for reference in references]


def lines(references) -> list[int]:
    return [reference.line for reference in references]


def blocks(parsed) -> list[tuple[int, int, str]]:
    return [(block.index, block.line, block.condition) for block in parsed.blocks]


def build(tmp_path, text, stems) -> pathlib.Path:
    root = tmp_path / "rulesets"
    (root / "rules").mkdir(parents=True)
    (root / "config.yaml").write_text(text, encoding="utf-8")
    for stem in stems:
        (root / "rules" / f"{stem}.md").write_text(f"text of {stem}\n", encoding="utf-8")
    return root


def received(root, *, model) -> set[str]:
    facts = Facts(model=model, agent=ABSENT, kind="session", flags=frozenset(), session=ABSENT)
    return {d.rule for d in compose(read_directory(root), facts, SessionState()).rules}


class TestTheReservedKeysAndBlocks:
    def test_a_config_using_every_reserved_key_and_one_block(self, tmp_path) -> None:
        root = build(
            tmp_path,
            "models: opus haiku\n"
            "flags: strict\n"
            "defaults: core.*\n"
            "sets:\n"
            "  core: sorting claims\n"
            "model haiku:\n"
            "  include: voice\n",
            ("sorting", "claims", "voice", "tone"),
        )

        assert check(root).errors == ()
        assert received(root, model="haiku") == {"sorting", "claims", "voice"}

    def test_a_config_whose_top_level_is_a_list_must_be_a_mapping_of_keys(self) -> None:
        with pytest.raises(config.ConfigParseError) as failure:
            parse("- defaults\n- models\n")

        assert failure.value.line == 1
        assert "must be a mapping of keys" in failure.value.reason

    def test_models_come_back_as_written(self) -> None:
        assert parse(SITUATION_ONE).models == ("opus", "sonnet", "haiku", "fable", "opus-4-8")

    def test_defaults_come_back_as_references_with_their_lines(self) -> None:
        defaults = parse(SITUATION_ONE).defaults

        assert texts(defaults.references) == ["all.*", "security-pass", "review-method"]
        assert [r.remove for r in defaults.references] == [False, True, True]
        assert lines(defaults.references) == [3, 4, 4]

    def test_each_set_comes_back_with_its_declaration_line_and_references(self) -> None:
        rulesets = parse(SITUATION_ONE).rulesets

        assert list(rulesets) == ["code", "reviewer"]
        assert (rulesets["code"].name, rulesets["code"].line) == ("code", 6)
        assert texts(rulesets["code"].references) == ["writing-code", "data-modeling"]
        assert (rulesets["reviewer"].name, rulesets["reviewer"].line) == ("reviewer", 7)
        assert texts(rulesets["reviewer"].references) == ["review-method", "report-format"]

    def test_each_block_comes_back_with_its_line_and_combined_condition(self) -> None:
        parsed = parse(SITUATION_ONE)

        assert blocks(parsed) == [
            (0, 8, "model haiku"),
            (1, 11, "agent critic and not model haiku"),
            (2, 13, "agent critic and flag strict"),
            (3, 15, "flag voice-terse"),
        ]
        assert [texts(block.references) for block in parsed.blocks] == [
            ["code.*"],
            ["reviewer.*"],
            ["security-pass"],
            ["voice@terse"],
        ]
        assert [lines(block.references) for block in parsed.blocks] == [[9], [12], [14], [16]]

    def test_a_valid_config_holds_no_problem(self) -> None:
        assert parse(SITUATION_ONE).problems == ()


class TestAListIsWords:
    def test_one_reference_per_line_under_include(self) -> None:
        parsed = parse(
            "agent Plan:\n  include:\n    reasoning.*\n    lookup.*\n    bash-commands\n"
        )

        (block,) = parsed.blocks
        assert texts(block.references) == ["reasoning.*", "lookup.*", "bash-commands"]
        assert lines(block.references) == [3, 4, 5]

    def test_a_sets_members_spanning_two_lines(self) -> None:
        parsed = parse("sets:\n  core: a b c d e\n    f g h i j\n")

        assert texts(parsed.rulesets["core"].references) == list("abcdefghij")
        assert lines(parsed.rulesets["core"].references) == [2] * 5 + [3] * 5

    def test_a_model_name_yaml_would_read_as_a_number_stays_as_written(self) -> None:
        assert parse("models: 4.5\n").models == ("4.5",)

    def test_a_reference_is_read_as_written_even_where_yaml_would_read_a_number(self) -> None:
        parsed = parse("defaults: 2024 yes\n")

        assert texts(parsed.defaults.references) == ["2024", "yes"]

    def test_a_list_written_as_a_yaml_sequence_holds_nothing_and_is_named(self) -> None:
        parsed = parse("flag strict:\n  include: [voice, tone]\n")

        assert parsed.blocks[0].references == ()
        assert parsed.problems == (WrongListShape("include", 2, "sequence"),)


class TestNestingAndThen:
    def test_a_nested_block_joins_its_condition_to_the_enclosing_one(self) -> None:
        parsed = parse("agent Plan:\n  not model haiku:\n    include: planning.*\n")

        assert blocks(parsed) == [(0, 2, "agent Plan and not model haiku")]

    def test_a_condition_holding_or_is_grouped_where_it_joins_another(self) -> None:
        parsed = parse("agent critic or agent auditor:\n  flag strict:\n    include: voice\n")

        assert parsed.blocks[0].condition == "(agent critic or agent auditor) and flag strict"

    def test_a_then_list_is_a_block_of_its_own_under_the_same_condition(self) -> None:
        parsed = parse(
            "model haiku:\n  include: writing-prose@haiku\n  then:\n    exclude: writing-prose\n"
        )

        assert blocks(parsed) == [(0, 1, "model haiku"), (1, 3, "model haiku")]
        assert [b.key for b in parsed.blocks] == ["model haiku", "then"]
        assert [texts(b.references) for b in parsed.blocks] == [
            ["writing-prose@haiku"],
            ["writing-prose"],
        ]

    def test_a_block_holding_only_nested_blocks_adds_no_list_of_its_own(self) -> None:
        parsed = parse("agent critic:\n  flag strict:\n    include: voice\n")

        assert blocks(parsed) == [(0, 2, "agent critic and flag strict")]


class TestAMissingOrEmptyConfig:
    def test_a_missing_config_reads_as_defaults_spreading_every_pool_rule(self, tmp_path) -> None:
        parsed = config.read_config(tmp_path)

        assert texts(parsed.defaults.references) == ["all.*"]
        assert parsed.models == ()
        assert dict(parsed.rulesets) == {}
        assert parsed.blocks == ()
        assert parsed.problems == ()

    def test_a_config_that_exists_is_read_from_config_yaml(self, tmp_path) -> None:
        (tmp_path / "config.yaml").write_text("defaults: voice\n", encoding="utf-8")
        (tmp_path / "manifest.yaml").write_text("defaults: tone\n", encoding="utf-8")

        parsed = config.read_config(tmp_path)

        assert texts(parsed.defaults.references) == ["voice"]
        assert parsed.path == tmp_path / "config.yaml"

    def test_an_empty_config_holds_nothing_rather_than_every_rule(self, tmp_path) -> None:
        (tmp_path / "config.yaml").write_text("# nothing yet\n", encoding="utf-8")

        parsed = config.read_config(tmp_path)

        assert parsed.defaults is None
        assert parsed.models == ()
        assert dict(parsed.rulesets) == {}
        assert parsed.blocks == ()
        assert parsed.problems == ()

    def test_a_key_written_with_no_value_holds_nothing(self) -> None:
        parsed = parse("models:\nflags:\ndefaults:\n")

        assert (parsed.models, parsed.flags) == ((), ())
        assert parsed.defaults.references == ()
        assert parsed.problems == ()


class TestAParseFailureIsNotAShapeError:
    def test_the_failure_names_the_file_and_line_in_its_message(self) -> None:
        with pytest.raises(config.ConfigParseError) as failure:
            parse("defaults: voice\nmodels: [opus, opus-4-8[1m]]\n")

        assert str(failure.value).startswith("config.yaml:2: ")

    def test_a_model_name_holding_brackets_parses_as_a_word(self) -> None:
        assert parse("models: opus opus-4-8[1m]\n").models == ("opus", "opus-4-8[1m]")

    def test_read_config_raises_for_a_file_that_does_not_parse(self, tmp_path) -> None:
        (tmp_path / "config.yaml").write_text("defaults: [a\n", encoding="utf-8")

        with pytest.raises(config.ConfigParseError) as failure:
            config.read_config(tmp_path)

        assert failure.value.path == tmp_path / "config.yaml"

    def test_a_wrong_shape_parses_into_a_config_and_names_its_problem(self) -> None:
        parsed = parse("defaults:\n  all: true\n")

        assert parsed.problems == (WrongKeyShape("defaults", 1),)


class TestAWrongShapeLeavesTheRestOfTheConfigStanding:
    def test_an_old_layout_key_is_named_and_holds_nothing(self) -> None:
        parsed = parse("defaults: voice\nwhen:\n  - flag a: ['voice']\nrulesets:\n  a: [b]\n")

        assert texts(parsed.defaults.references) == ["voice"]
        assert parsed.blocks == ()
        assert parsed.problems == (OldLayoutKey("when", 2), OldLayoutKey("rulesets", 4))

    def test_models_written_as_a_mapping_holds_nothing(self) -> None:
        parsed = parse("models:\n  opus: 1\n")

        assert parsed.models == ()
        assert parsed.problems == (WrongKeyShape("models", 1),)

    def test_models_written_as_a_dash_list_is_one_list_problem(self) -> None:
        parsed = parse("models:\n  - opus\n")

        assert parsed.models == ()
        assert parsed.problems == (WrongListShape("models", 2, "sequence"),)

    def test_sets_that_is_not_a_mapping_holds_nothing(self) -> None:
        parsed = parse("sets: code\n")

        assert dict(parsed.rulesets) == {}
        assert parsed.problems == (WrongKeyShape("sets", 1),)

    def test_a_set_whose_value_is_neither_words_nor_include_and_exclude_holds_nothing(self) -> None:
        parsed = parse("sets:\n  code:\n    a: b\n  tone: voice\n")

        assert parsed.rulesets["code"].references == ()
        assert parsed.rulesets["code"].line == 2
        assert texts(parsed.rulesets["tone"].references) == ["voice"]
        assert parsed.problems == (WrongRulesetShape("code", 2),)

    def test_a_set_holding_include_and_exclude_forms_one_list(self) -> None:
        parsed = parse("sets:\n  lean:\n    include: all.*\n    exclude: prose.voice\n")

        references = parsed.rulesets["lean"].references
        assert [(r.text, r.remove) for r in references] == [("all.*", False), ("prose.voice", True)]

    def test_a_reserved_set_declaration_is_skipped_and_named(self) -> None:
        parsed = parse("sets:\n  all: voice\n  none:\n  tone: voice\n")

        assert list(parsed.rulesets) == ["tone"]
        assert parsed.problems == (
            ReservedRulesetDeclared("all", 2),
            ReservedRulesetDeclared("none", 3),
        )

    def test_a_set_named_defaults_or_rules_is_reserved_too(self) -> None:
        parsed = parse("sets:\n  defaults: voice\n  rules: voice\n")

        assert dict(parsed.rulesets) == {}
        assert parsed.problems == (
            ReservedRulesetDeclared("defaults", 2),
            ReservedRulesetDeclared("rules", 3),
        )

    def test_a_set_name_holding_a_dot_is_skipped_and_named(self) -> None:
        parsed = parse("sets:\n  code.extra: voice\n")

        assert dict(parsed.rulesets) == {}
        assert parsed.problems == (DottedRulesetName("code.extra", 2),)

    def test_a_block_of_the_wrong_shape_is_skipped_and_named(self) -> None:
        parsed = parse(
            "flag a:\n"
            "  include: voice\n"
            "agent critic: reasoning.* lookup.*\n"
            "agent auditor: {}\n"
            "agent Plan:\n"
            "  - voice\n"
            "flag e:\n"
            "  include: voice\n"
        )

        assert [b.condition for b in parsed.blocks] == ["flag a", "flag e"]
        assert parsed.problems == (
            WrongBlockShape("agent critic", "agent critic", 3, "words"),
            WrongBlockShape("agent auditor", "agent auditor", 4, "empty"),
            WrongBlockShape("agent Plan", "agent Plan", 5, "sequence"),
        )

    def test_a_key_written_twice_in_one_mapping_skips_every_copy(self) -> None:
        parsed = parse(
            "model haiku:\n"
            "  include: voice\n"
            "flag a:\n"
            "  include: tone\n"
            "model haiku:\n"
            "  include: claims\n"
        )

        assert [b.condition for b in parsed.blocks] == ["flag a"]
        assert parsed.problems == (DuplicateKey("model haiku", (1, 5)),)

    def test_the_config_keeps_the_path_it_was_read_from(self) -> None:
        parsed = config.parse_config("defaults: x\n", pathlib.Path("/pool/config.yaml"))

        assert parsed.path == pathlib.Path("/pool/config.yaml")

    def test_one_model_name_declared_twice_is_no_problem(self) -> None:
        assert parse("models: sonnet sonnet\n").problems == ()
