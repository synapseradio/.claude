#!/usr/bin/env python3
"""Check reports every illegal state of a rulesets directory as an error with its subject.

The check serves the engineer who edits a config or a rule file and runs check before
trusting a delivery: each error names its kind, the subject delivery will disable, and the
file and line to open, and one run reports every error together. There is one case per row of
the error table in design.md "Explain and check", plus the cases that must stay silent. Each
case builds its rulesets directory under `tmp_path`.

Run with `python3.15 -m pytest features/plugins/rulesets/tests/test_check_errors.py`.
"""

import os
import pathlib
import sys

import pytest

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]

sys.path.insert(0, str(PLUGIN_ROOT / "lib"))

from rulesets.check.findings import (  # noqa: E402  # noqa: E402
    BlockSubject,
    ConfigSubject,
    DirectorySubject,
    ErrorKind,
    KeySubject,
    ReferencesSubject,
    ReferenceSubject,
    RulesetsSubject,
    RulesetSubject,
    RuleSubject,
    Subject,
)
from rulesets.check.report_format import finding_line  # noqa: E402
from rulesets.check.run import check  # noqa: E402  (path must be set before this import)
from rulesets.compose.composition import compose  # noqa: E402
from rulesets.facts.context import ABSENT, Facts  # noqa: E402
from rulesets.session.state import SessionState  # noqa: E402
from rulesets.source.directory import read_directory  # noqa: E402


def build(tmp_path, config=None, stems=(), bodies=None) -> pathlib.Path:
    """A rulesets directory with the config text, a file per stem, and any given bodies."""
    root = tmp_path / "rulesets"
    (root / "rules").mkdir(parents=True)
    if config is not None:
        (root / "config.yaml").write_text(config, encoding="utf-8")
    texts = {stem: f"text of {stem}\n" for stem in stems} | (bodies or {})
    for stem, text in texts.items():
        (root / "rules" / f"{stem}.md").write_text(text, encoding="utf-8")
    return root


def errors_of(root) -> list[tuple[ErrorKind, Subject, int | None]]:
    return [(error.kind, error.subject, error.line) for error in check(root).errors]


class TestARulesetCycle:
    def test_a_cycle_is_one_error_naming_every_ruleset_in_it_at_the_first_one_written(
        self, tmp_path
    ) -> None:
        root = build(
            tmp_path,
            ("sets:\n  a: b.*\n  b: a.*\n  c: voice\n"),
            stems=["voice"],
        )

        assert errors_of(root) == [("ruleset-cycle", RulesetsSubject(("a", "b")), 2)]

    def test_a_ruleset_that_only_spreads_into_a_cycle_is_no_error(self, tmp_path) -> None:
        root = build(tmp_path, ("sets:\n  a: b.*\n  b: a.*\n  c: a.*\n"))

        assert [subject for _, subject, _ in errors_of(root)] == [RulesetsSubject(("a", "b"))]

    def test_a_ruleset_spreading_itself_is_a_cycle(self, tmp_path) -> None:
        root = build(tmp_path, ("sets:\n  a: a.*\n"))

        assert errors_of(root) == [("ruleset-cycle", RulesetsSubject(("a",)), 2)]

    def test_a_cycle_through_defaults_is_one_error_at_the_first_member_written(
        self, tmp_path
    ) -> None:
        root = build(tmp_path, ("defaults: a.*\nsets:\n  a: defaults.*\n"))

        assert errors_of(root) == [("ruleset-cycle", RulesetsSubject(("a", "defaults")), 1)]

    def test_the_message_says_the_spreads_form_a_cycle_and_reach_no_rule(self, tmp_path) -> None:
        root = build(tmp_path, ("sets:\n  a: b.*\n  b: a.*\n"))

        (error,) = check(root).errors
        assert error.subject == RulesetsSubject(("a", "b"))
        assert "cycle" in error.message
        assert "reaches no rule" in error.message

    def test_the_error_names_the_config_file(self, tmp_path) -> None:
        root = build(tmp_path, ("sets:\n  a: a.*\n"))

        assert check(root).errors[0].file == root / "config.yaml"


class TestOneListSettingTwoVariantsOfOneRule:
    def test_the_two_references_are_the_subject(self, tmp_path) -> None:
        root = build(
            tmp_path,
            "defaults: voice@terse voice@warm\n",
            stems=["voice", "voice@terse", "voice@warm"],
        )

        assert errors_of(root) == [
            (
                "variant-conflict",
                ReferencesSubject(
                    (ReferenceSubject("voice@terse", 1), ReferenceSubject("voice@warm", 1))
                ),
                1,
            )
        ]

    def test_the_conflict_sits_in_a_ruleset_as_well_as_in_defaults(self, tmp_path) -> None:
        root = build(
            tmp_path,
            ("sets:\n  tone: voice@terse voice@warm\n"),
            stems=["voice", "voice@terse", "voice@warm"],
        )

        assert [kind for kind, _, _ in errors_of(root)] == ["variant-conflict"]

    def test_the_conflict_sits_in_a_block_list(self, tmp_path) -> None:
        root = build(
            tmp_path,
            ("flags: a\nflag a:\n  include: voice@terse voice@warm\n"),
            stems=["voice", "voice@terse", "voice@warm"],
        )

        assert [kind for kind, _, _ in errors_of(root)] == ["variant-conflict"]

    def test_two_blocks_for_different_models_setting_different_variants_are_no_error(
        self, tmp_path
    ) -> None:
        root = build(
            tmp_path,
            "models: opus sonnet\n"
            "model opus:\n"
            "  include: voice@terse\n"
            "model sonnet:\n"
            "  include: voice@warm\n",
            stems=["voice", "voice@terse", "voice@warm"],
        )

        assert errors_of(root) == []

    def test_one_variant_named_twice_is_no_conflict(self, tmp_path) -> None:
        root = build(
            tmp_path,
            "defaults: voice@terse voice@terse\n",
            stems=["voice", "voice@terse"],
        )

        assert errors_of(root) == []

    def test_a_strike_that_leaves_one_variant_is_no_conflict(self, tmp_path) -> None:
        root = build(
            tmp_path,
            ("defaults:\n  include: voice@terse voice@warm\n  exclude: voice@warm\n"),
            stems=["voice", "voice@terse", "voice@warm"],
        )

        assert errors_of(root) == []


class TestAConditionThatTestsMoreThanFacts:
    def test_a_test_of_a_project_is_an_error_whose_subject_is_the_block(self, tmp_path) -> None:
        root = build(tmp_path, ("project amboss:\n  include: voice\n"), stems=["voice"])

        assert errors_of(root) == [("condition-invalid", BlockSubject("project amboss"), 1)]

    def test_the_message_names_what_the_condition_tests(self, tmp_path) -> None:
        root = build(tmp_path, ("env CI:\n  include: voice\n"), stems=["voice"])

        assert "env" in check(root).errors[0].message

    def test_text_that_does_not_parse_is_an_error_whose_subject_is_the_block(
        self, tmp_path
    ) -> None:
        root = build(
            tmp_path, ("(agent critic and flag strict:\n  include: voice\n"), stems=["voice"]
        )

        assert errors_of(root) == [
            ("condition-invalid", BlockSubject("(agent critic and flag strict"), 1)
        ]

    def test_a_nested_block_is_named_by_its_combined_condition_at_its_own_line(
        self, tmp_path
    ) -> None:
        root = build(
            tmp_path,
            ("flags: ok\nflag ok:\n  include: voice\n  project x:\n    include: voice\n"),
            stems=["voice"],
        )

        assert errors_of(root) == [("condition-invalid", BlockSubject("flag ok and project x"), 4)]

    def test_an_agent_nobody_declares_is_no_error(self, tmp_path) -> None:
        root = build(tmp_path, ("agent eval-runner:\n  include: voice\n"), stems=["voice"])

        assert errors_of(root) == []

    def test_a_declared_flag_nobody_sets_is_no_error(self, tmp_path) -> None:
        root = build(tmp_path, ("flags: strict\nflag strict:\n  include: voice\n"), stems=["voice"])

        assert errors_of(root) == []

    def test_a_correct_condition_is_no_error(self, tmp_path) -> None:
        root = build(
            tmp_path,
            ("models: haiku\n(agent a or kind delegate) and not model haiku:\n  include: voice\n"),
            stems=["voice"],
        )

        assert errors_of(root) == []


class TestAConditionNamingAModelTheConfigDoesNotDeclare:
    def test_the_block_is_the_subject(self, tmp_path) -> None:
        root = build(
            tmp_path,
            ("models: opus\nmodel hiaku:\n  include: voice\n"),
            stems=["voice"],
        )

        assert errors_of(root) == [("unknown-model", BlockSubject("model hiaku"), 2)]

    def test_the_message_names_the_model(self, tmp_path) -> None:
        root = build(tmp_path, ("models: opus\nmodel hiaku:\n  include: voice\n"), stems=["voice"])

        assert "hiaku" in check(root).errors[0].message

    def test_a_config_declaring_no_models_declares_none(self, tmp_path) -> None:
        root = build(tmp_path, ("model haiku:\n  include: voice\n"), stems=["voice"])

        assert errors_of(root) == [("unknown-model", BlockSubject("model haiku"), 1)]

    def test_a_negated_model_test_is_checked_too(self, tmp_path) -> None:
        root = build(
            tmp_path, ("models: opus\nnot model nova:\n  include: voice\n"), stems=["voice"]
        )

        assert errors_of(root) == [("unknown-model", BlockSubject("not model nova"), 2)]

    def test_each_undeclared_name_of_one_block_is_named_in_one_error(self, tmp_path) -> None:
        root = build(tmp_path, ("model nova or model luna:\n  include: voice\n"), stems=["voice"])

        (error,) = check(root).errors
        assert "nova" in error.message
        assert "luna" in error.message

    def test_an_undeclared_value_inside_a_group_is_named_as_it_would_be_alone(
        self, tmp_path
    ) -> None:
        grouped = build(
            tmp_path / "grouped",
            ("models: opus\nmodel opus opus-9:\n  include: voice\n"),
            stems=["voice"],
        )
        alone = build(
            tmp_path / "alone",
            ("models: opus\nmodel opus-9:\n  include: voice\n"),
            stems=["voice"],
        )

        (grouped_error,) = check(grouped).errors
        (alone_error,) = check(alone).errors

        assert (grouped_error.kind, grouped_error.line) == ("unknown-model", 2)
        assert "names `opus-9`, which the config does not declare" in grouped_error.message
        assert "`opus`," not in grouped_error.message
        assert (alone_error.kind, alone_error.line) == ("unknown-model", 2)
        assert "names `opus-9`, which the config does not declare" in alone_error.message

    def test_a_declared_model_is_no_error(self, tmp_path) -> None:
        root = build(tmp_path, ("models: opus\nmodel opus:\n  include: voice\n"), stems=["voice"])

        assert errors_of(root) == []


class TestABlockOfTheWrongShape:
    def test_a_block_holding_one_word_is_an_error_naming_the_block(self, tmp_path) -> None:
        root = build(tmp_path, "agent critic: voice\n", stems=["voice"])

        assert errors_of(root) == [("block-shape", BlockSubject("agent critic"), 1)]

    def test_a_block_holding_words_with_no_include_says_they_belong_under_include(
        self, tmp_path
    ) -> None:
        root = build(tmp_path, "agent critic: reasoning.* lookup.*\n")

        (error,) = check(root).errors

        assert (error.kind, error.subject, error.line) == (
            "block-shape",
            BlockSubject("agent critic"),
            1,
        )
        assert "belong under `include`" in error.message

    def test_a_block_holding_an_empty_mapping_says_it_holds_no_list_and_no_nested_block(
        self, tmp_path
    ) -> None:
        root = build(tmp_path, "agent critic: {}\n")

        (error,) = check(root).errors

        assert (error.kind, error.subject, error.line) == (
            "block-shape",
            BlockSubject("agent critic"),
            1,
        )
        assert "holds no list and no nested block" in error.message

    def test_a_block_holding_nothing_at_all_is_the_same_error(self, tmp_path) -> None:
        root = build(tmp_path, "agent critic:\n")

        (error,) = check(root).errors

        assert (error.kind, error.subject) == ("block-shape", BlockSubject("agent critic"))
        assert "holds no list and no nested block" in error.message

    def test_a_block_holding_a_dash_list_says_a_list_is_words(self, tmp_path) -> None:
        root = build(tmp_path, "agent critic:\n  - voice\n", stems=["voice"])

        (error,) = check(root).errors

        assert (error.kind, error.subject) == ("block-shape", BlockSubject("agent critic"))
        assert "a list is words" in error.message

    def test_the_rest_of_the_config_still_delivers_and_checks(self, tmp_path) -> None:
        root = build(tmp_path, "agent critic: voice\ndefaults: ghost\n", stems=["voice"])

        assert [kind for kind, _, _ in errors_of(root)] == [
            "block-shape",
            "undeclared-reference",
        ]


class TestAReferenceNamingWhatNothingDeclares:
    def test_an_undeclared_rule_is_an_error_whose_subject_is_the_reference(self, tmp_path) -> None:
        root = build(tmp_path, "defaults: voice ghost\n", stems=["voice"])

        assert errors_of(root) == [("undeclared-reference", ReferenceSubject("ghost", 1), 1)]

    def test_the_third_reference_of_a_list_is_cited_at_its_own_line(self, tmp_path) -> None:
        root = build(
            tmp_path,
            ("agent critic:\n  include:\n    voice\n    tone\n    ghost\n"),
            stems=["voice", "tone"],
        )

        assert errors_of(root) == [("undeclared-reference", ReferenceSubject("ghost", 5), 5)]

    def test_the_message_names_the_rule(self, tmp_path) -> None:
        root = build(tmp_path, "defaults: ghost\n")

        assert "ghost" in check(root).errors[0].message

    def test_the_printed_line_names_the_reference_once_before_the_cause(self, tmp_path) -> None:
        root = build(tmp_path, "defaults: ghost\n")

        (error,) = check(root).errors

        assert finding_line(error) == (
            f"{root / 'config.yaml'}:1: error [undeclared-reference] "
            "reference `ghost`: the pool holds no rule `ghost`"
        )

    def test_each_cause_is_worded_without_repeating_the_reference(self, tmp_path) -> None:
        root = build(
            tmp_path,
            "defaults: rules.ghost voice@loud phantom.* foo:bar\n",
            stems=["voice"],
        )

        assert [(e.kind, e.message) for e in check(root).errors] == [
            ("undeclared-reference", "the pool holds no rule `ghost`"),
            ("undeclared-reference", "rule `voice` has no variant `loud`"),
            ("undeclared-reference", "no ruleset `phantom` is declared"),
            (
                "malformed-reference",
                "not a reference form; write rule, rule@variant, set.rule, set.rule@variant, "
                "or set.*",
            ),
        ]

    def test_an_undeclared_variant_is_an_error(self, tmp_path) -> None:
        root = build(tmp_path, "defaults: voice@loud\n", stems=["voice", "voice@terse"])

        assert errors_of(root) == [("undeclared-reference", ReferenceSubject("voice@loud", 1), 1)]

    def test_an_undeclared_ruleset_is_an_error(self, tmp_path) -> None:
        root = build(tmp_path, "defaults: phantom.*\n", stems=["voice"])

        assert errors_of(root) == [("undeclared-reference", ReferenceSubject("phantom.*", 1), 1)]

    def test_an_exclude_of_an_undeclared_rule_is_an_error_at_its_line(self, tmp_path) -> None:
        root = build(tmp_path, ("defaults:\n  include: all.*\n  exclude: ghost\n"), stems=["voice"])

        assert errors_of(root) == [("undeclared-reference", ReferenceSubject("ghost", 3), 3)]

    def test_an_undeclared_reference_inside_a_ruleset_and_a_block_is_found(self, tmp_path) -> None:
        root = build(
            tmp_path,
            ("flags: a\nsets:\n  code: ghost\nflag a:\n  include: spook\n"),
            stems=["voice"],
        )

        assert errors_of(root) == [
            ("undeclared-reference", ReferenceSubject("ghost", 3), 3),
            ("undeclared-reference", ReferenceSubject("spook", 5), 5),
        ]

    def test_a_reference_reached_by_two_spreads_is_reported_once(self, tmp_path) -> None:
        root = build(
            tmp_path,
            ("defaults: a.* b.*\nsets:\n  a: ghost\n  b: a.*\n"),
            stems=["voice"],
        )

        assert errors_of(root) == [("undeclared-reference", ReferenceSubject("ghost", 3), 3)]

    def test_text_that_is_no_reference_form_is_an_error(self, tmp_path) -> None:
        root = build(tmp_path, "defaults: foo:bar\n")

        assert errors_of(root) == [("malformed-reference", ReferenceSubject("foo:bar", 1), 1)]

    def test_a_declared_variant_and_ruleset_are_no_error(self, tmp_path) -> None:
        root = build(
            tmp_path,
            ("defaults: voice@terse tone.*\nsets:\n  tone: voice\n"),
            stems=["voice", "voice@terse"],
        )

        assert errors_of(root) == []


class TestARulesetOfTheWrongShape:
    def test_a_mapping_holding_another_key_names_the_declaration(self, tmp_path) -> None:
        root = build(
            tmp_path,
            ("sets:\n  code:\n    a: b\n  tone: voice\n"),
            stems=["voice"],
        )

        assert errors_of(root) == [("ruleset-shape", RulesetSubject("code"), 2)]

    def test_a_name_holding_a_dot_is_an_error_saying_a_name_holds_no_dot(self, tmp_path) -> None:
        root = build(tmp_path, ("sets:\n  code.extra: voice\n"), stems=["voice"])

        (error,) = check(root).errors

        assert (error.kind, error.subject, error.line) == (
            "ruleset-name",
            RulesetSubject("code.extra"),
            2,
        )
        assert "holds no `.`" in error.message
        assert "`code.extra`" in finding_line(error)


class TestAReservedRulesetDeclared:
    def test_each_reserved_name_is_an_error_naming_the_declaration(self, tmp_path) -> None:
        root = build(
            tmp_path,
            ("sets:\n  defaults:\n  all:\n  rules:\n  none:\n"),
        )

        assert errors_of(root) == [
            ("reserved-ruleset", RulesetSubject("defaults"), 2),
            ("reserved-ruleset", RulesetSubject("all"), 3),
            ("reserved-ruleset", RulesetSubject("rules"), 4),
            ("reserved-ruleset", RulesetSubject("none"), 5),
        ]


class TestARuleWhoseFrontmatterCarriesACondition:
    def test_the_rule_is_the_subject_and_the_condition_line_is_the_line(self, tmp_path) -> None:
        root = build(
            tmp_path,
            "defaults: voice\n",
            bodies={"voice": "---\ndescription: tone\nmodel: haiku\n---\ntext\n"},
        )

        (error,) = check(root).errors
        assert (error.kind, error.subject, error.line) == (
            "rule-condition",
            RuleSubject("voice"),
            3,
        )
        assert error.file == root / "rules" / "voice.md"

    def test_a_path_scope_is_a_condition(self, tmp_path) -> None:
        root = build(tmp_path, bodies={"voice": "---\npaths:\n  - src/**\n---\ntext\n"})

        assert errors_of(root) == [("rule-condition", RuleSubject("voice"), 2)]

    def test_a_variant_file_carrying_a_condition_names_that_file(self, tmp_path) -> None:
        root = build(
            tmp_path,
            stems=["voice"],
            bodies={"voice@terse": "---\nagent: critic\n---\ntext\n"},
        )

        (error,) = check(root).errors
        assert error.subject == RuleSubject("voice")
        assert error.file == root / "rules" / "voice@terse.md"

    @pytest.mark.parametrize(
        "key",
        ["paths", "when", "model", "models", "agent", "agents", "kind", "kinds", "flag", "flags"],
    )
    def test_each_key_a_condition_can_test_is_a_condition(self, tmp_path, key) -> None:
        root = build(tmp_path, bodies={"voice": f"---\n{key}: x\n---\ntext\n"})

        assert errors_of(root) == [("rule-condition", RuleSubject("voice"), 2)]

    def test_the_first_condition_key_in_file_order_is_the_one_named(self, tmp_path) -> None:
        root = build(tmp_path, bodies={"voice": "---\ndescription: x\nflags: a\nmodel: b\n---\n"})

        (error,) = check(root).errors
        assert (error.line, "`flags`" in error.message) == (3, True)

    def test_frontmatter_without_a_condition_is_no_error(self, tmp_path) -> None:
        root = build(tmp_path, bodies={"voice": "---\ndescription: tone\n---\ntext\n"})

        assert errors_of(root) == []

    def test_frontmatter_that_does_not_parse_is_an_error_on_the_rule_and_no_warning(
        self, tmp_path
    ) -> None:
        root = build(tmp_path, bodies={"voice": "---\npaths: [unclosed\n---\ntext\n"})

        report = check(root)

        (error,) = report.errors
        assert (error.kind, error.subject) == ("frontmatter-unparsable", RuleSubject("voice"))
        assert error.file == root / "rules" / "voice.md"
        assert report.warnings == ()

    def test_a_fence_closed_with_no_trailing_newline_still_carries_a_condition(
        self, tmp_path
    ) -> None:
        root = build(tmp_path)
        (root / "rules" / "voice.md").write_bytes(b"---\r\nmodel: haiku\r\n---")

        assert errors_of(root) == [("rule-condition", RuleSubject("voice"), 2)]


class TestAVariantBesideNoDefaultForm:
    def test_the_rule_is_the_subject(self, tmp_path) -> None:
        root = build(tmp_path, stems=["tone@dry"])

        (error,) = check(root).errors
        assert (error.kind, error.subject) == ("variant-without-default", RuleSubject("tone"))
        assert error.file == root / "rules" / "tone@dry.md"

    def test_a_variant_beside_its_default_is_no_error(self, tmp_path) -> None:
        root = build(tmp_path, stems=["tone", "tone@dry"])

        assert errors_of(root) == []


class TestARuleFileThatCannotBeRead:
    def test_a_file_that_is_not_utf8_is_an_error_whose_subject_is_the_rule(self, tmp_path) -> None:
        root = build(tmp_path, stems=["other"])
        (root / "rules" / "voice.md").write_bytes(b"Speak \xff\xfe plainly.\n")

        (error,) = check(root).errors

        assert (error.kind, error.subject, error.line) == (
            "unreadable-file",
            RuleSubject("voice"),
            None,
        )
        assert error.file == root / "rules" / "voice.md"
        assert "UTF-8" in error.message

    def test_the_unreadable_file_draws_no_other_finding(self, tmp_path) -> None:
        root = build(tmp_path)
        (root / "rules" / "voice.md").write_bytes(b"\xff\xfe")

        report = check(root)

        assert [error.kind for error in report.errors] == ["unreadable-file"]
        assert report.warnings == ()

    def test_every_unreadable_file_of_a_rule_is_reported(self, tmp_path) -> None:
        root = build(tmp_path)
        (root / "rules" / "voice.md").write_bytes(b"\xff")
        (root / "rules" / "voice@terse.md").write_bytes(b"\xfe")

        assert [(kind, subject) for kind, subject, _ in errors_of(root)] == [
            ("unreadable-file", RuleSubject("voice")),
            ("unreadable-file", RuleSubject("voice")),
        ]

    def test_the_other_errors_of_the_run_still_arrive(self, tmp_path) -> None:
        root = build(tmp_path, "when: x\n")
        (root / "rules" / "voice.md").write_bytes(b"\xff")

        assert [kind for kind, _, _ in errors_of(root)] == ["old-layout", "unreadable-file"]


class TestATopLevelKeyTheConfigDoesNotDefine:
    def test_a_key_that_tests_no_fact_is_an_error_naming_the_key(self, tmp_path) -> None:
        root = build(
            tmp_path,
            ("defaults: voice\nprojekt:\n  include: voice\n"),
            stems=["voice"],
        )

        (error,) = check(root).errors

        assert (error.kind, error.subject, error.line) == (
            "condition-invalid",
            BlockSubject("projekt"),
            2,
        )
        assert "`projekt`" in error.message

    def test_a_key_holding_one_word_is_an_error_naming_the_key(self, tmp_path) -> None:
        root = build(tmp_path, "defaults: voice\nproject: amboss\n", stems=["voice"])

        assert errors_of(root) == [("block-shape", BlockSubject("project"), 2)]


class TestTheConfigInTheOldLayout:
    def test_a_when_key_is_an_error_saying_each_condition_is_a_top_level_key(
        self, tmp_path
    ) -> None:
        root = build(
            tmp_path,
            ("defaults: voice\nwhen:\n  - flag a: ['voice']\n  - model haiku: ['voice']\n"),
            stems=["voice"],
        )

        (error,) = check(root).errors

        assert (error.kind, error.subject, error.line) == ("old-layout", KeySubject("when"), 2)
        assert "each condition is a top-level key" in error.message

    def test_a_rulesets_key_is_an_error_naming_sets(self, tmp_path) -> None:
        root = build(tmp_path, "rulesets:\n  code: voice\n", stems=["voice"])

        (error,) = check(root).errors

        assert (error.kind, error.subject, error.line) == (
            "old-layout",
            KeySubject("rulesets"),
            1,
        )
        assert "`sets`" in error.message

    def test_a_bracketed_list_of_quoted_entries_is_an_error_saying_a_list_is_words(
        self, tmp_path
    ) -> None:
        root = build(
            tmp_path,
            (
                "sets:\n"
                "  reasoning: voice\n"
                "  lookup: tone\n"
                "agent critic:\n"
                '  include: ["reasoning.*", "lookup.*"]\n'
            ),
            stems=["voice", "tone"],
        )

        (error,) = check(root).errors

        assert (error.kind, error.subject, error.line) == ("list-shape", KeySubject("include"), 5)
        assert error.message.startswith("a list is words, one or more per line")

    def test_a_dash_list_is_the_same_error_at_its_first_line(self, tmp_path) -> None:
        root = build(tmp_path, "defaults:\n  - voice\n  - tone\n", stems=["voice", "tone"])

        assert errors_of(root) == [("list-shape", KeySubject("defaults"), 2)]

    def test_a_bracketed_model_list_is_one_error(self, tmp_path) -> None:
        root = build(tmp_path, "models: [opus, sonnet]\n")

        assert errors_of(root) == [("list-shape", KeySubject("models"), 1)]

    def test_a_list_in_the_old_form_delivers_none_of_its_rules(self, tmp_path) -> None:
        root = build(tmp_path, "defaults: ['voice']\n", stems=["voice", "tone"])

        warnings = [(w.kind, w.subject) for w in check(root).warnings]

        assert ("never-included", RuleSubject("voice")) in warnings


class TestAConditionKeyWrittenTwice:
    def test_both_lines_are_named_with_then_and_neither_block_delivers(self, tmp_path) -> None:
        filler = "".join(f"# line {n}\n" for n in range(2, 20))
        root = build(
            tmp_path,
            "models: haiku\n" + filler + "model haiku:\n"
            "  include: voice\n"
            + "".join(f"# line {n}\n" for n in range(22, 30))
            + "model haiku:\n"
            "  include: tone\n",
            stems=["voice", "tone"],
        )

        (error,) = check(root).errors
        facts = Facts(
            model="haiku", agent=ABSENT, kind="session", flags=frozenset(), session=ABSENT
        )
        delivered = compose(read_directory(root), facts, SessionState()).rules

        assert (error.kind, error.subject, error.line) == (
            "duplicate-key",
            KeySubject("model haiku"),
            20,
        )
        assert "20" in error.message
        assert "30" in error.message
        assert "`then`" in error.message
        assert [rule.rule for rule in delivered] == []


class TestEveryConfigShapeErrorIsWordedForTheFileToOpen:
    def test_each_kind_names_the_config_file_and_says_what_is_wrong(self, tmp_path) -> None:
        text = (
            "models:\n"
            "  opus: x\n"
            "sets:\n"
            "  code:\n"
            "    a: b\n"
            "  all:\n"
            "when:\n"
            "  - flag a: voice\n"
            "agent critic: {}\n"
        )
        root = build(tmp_path, text)

        errors = check(root).errors

        assert {error.file for error in errors} == {root / "config.yaml"}
        assert [(error.kind, error.message) for error in errors] == [
            (
                "key-shape",
                "`models` must be model names; a list is words, one or more per line, "
                "with no quotes, brackets, or dashes",
            ),
            (
                "ruleset-shape",
                "ruleset `code` must be references, or a mapping of `include` and `exclude`",
            ),
            ("reserved-ruleset", "`all` is a reserved ruleset and cannot be declared"),
            (
                "old-layout",
                "the config no longer reads `when`; each condition is a top-level key, "
                "its rules under `include` and `exclude`",
            ),
            (
                "block-shape",
                "it holds no list and no nested block; give it `include`, `exclude`, or a block",
            ),
        ]


class TestATopLevelValueOfTheWrongShape:
    def test_defaults_holding_another_key_names_the_key(self, tmp_path) -> None:
        root = build(tmp_path, "defaults:\n  all: true\n")

        assert errors_of(root) == [("key-shape", KeySubject("defaults"), 1)]

    def test_each_declaration_key_has_a_shape(self, tmp_path) -> None:
        root = build(
            tmp_path,
            ("models:\n  a: b\nflags:\n  c: d\ndefaults:\n  e: f\nsets: x\n"),
        )

        assert errors_of(root) == [
            ("key-shape", KeySubject("models"), 1),
            ("key-shape", KeySubject("flags"), 3),
            ("key-shape", KeySubject("defaults"), 5),
            ("key-shape", KeySubject("sets"), 7),
        ]


class TestAConfigThatDoesNotParse:
    def test_a_bracketed_model_name_holding_brackets_is_an_error_at_its_line(
        self, tmp_path
    ) -> None:
        root = build(tmp_path, "defaults: voice\nmodels: [opus, opus-4-8[1m]]\n", stems=["voice"])

        (error,) = check(root).errors
        assert (error.kind, error.subject, error.line) == (
            "config-unparsable",
            ConfigSubject(),
            2,
        )
        assert error.file == root / "config.yaml"

    def test_a_config_that_is_not_utf8_is_unparsable_and_names_the_cause_and_line(
        self, tmp_path
    ) -> None:
        root = build(tmp_path)
        (root / "config.yaml").write_bytes(b"defaults: all.*\nmodels: \xff\n")

        (error,) = check(root).errors

        assert (error.kind, error.subject, error.line) == (
            "config-unparsable",
            ConfigSubject(),
            2,
        )
        assert error.file == root / "config.yaml"
        assert "UTF-8" in error.message

    def test_a_config_decode_error_far_into_the_file_names_its_line(self, tmp_path) -> None:
        root = build(tmp_path)
        filler = b"# padding\n" * 2000
        (root / "config.yaml").write_bytes(filler + b"models: \xff\n")

        (error,) = check(root).errors

        assert (error.kind, error.line) == ("config-unparsable", 2001)

    @pytest.mark.skipif(os.geteuid() == 0, reason="root reads a file whatever its mode")
    def test_a_config_the_system_cannot_open_is_unparsable_with_no_line(self, tmp_path) -> None:
        root = build(tmp_path)
        (root / "config.yaml").write_text("defaults: all.*\n", encoding="utf-8")
        (root / "config.yaml").chmod(0)

        (error,) = check(root).errors

        assert (error.kind, error.subject, error.line) == (
            "config-unparsable",
            ConfigSubject(),
            None,
        )
        assert error.message

    def test_a_model_name_holding_brackets_written_as_a_word_is_no_error(self, tmp_path) -> None:
        root = build(tmp_path, "models: opus opus-4-8[1m]\n")

        assert errors_of(root) == []

    def test_rule_file_errors_are_still_reported(self, tmp_path) -> None:
        root = build(tmp_path, "models: [opus-4-8[1m]]\n", stems=["tone@dry"])

        assert [kind for kind, _, _ in errors_of(root)] == [
            "config-unparsable",
            "variant-without-default",
        ]


class TestABareStar:
    def test_a_bare_star_under_include_is_an_error_at_its_line_naming_all(self, tmp_path) -> None:
        root = build(tmp_path, "agent critic:\n  include:\n    voice\n    *\n", stems=["voice"])

        (error,) = check(root).errors

        assert (error.kind, error.line) == ("old-reference", 4)
        assert "`all.*`" in error.message

    def test_a_bare_star_opening_a_value_fails_to_parse_and_names_all(self, tmp_path) -> None:
        root = build(tmp_path, "defaults: *\n")

        (error,) = check(root).errors

        assert error.kind == "config-unparsable"
        assert "`all.*`" in error.message

    def test_a_parse_failure_with_another_cause_carries_no_advice(self, tmp_path) -> None:
        root = build(tmp_path, "defaults: 'unterminated\n")

        (error,) = check(root).errors

        assert error.kind == "config-unparsable"
        assert "`all.*`" not in error.message


class TestABodyLongerThanThePartBudget:
    def test_a_body_of_twelve_thousand_characters_is_an_error_naming_its_rule_and_file(
        self, tmp_path
    ) -> None:
        root = build(tmp_path, bodies={"voice": "x" * 12_000})

        (error,) = check(root).errors
        assert (error.kind, error.subject) == ("oversize-body", RuleSubject("voice"))
        assert error.file == root / "rules" / "voice.md"
        assert check(root).warnings == ()

    def test_a_body_that_with_its_marker_is_exactly_nine_thousand_characters_is_no_error(
        self, tmp_path
    ) -> None:
        root = build(tmp_path, bodies={"voice": "x" * 8_978})

        assert errors_of(root) == []

    def test_a_body_one_character_longer_is_an_error(self, tmp_path) -> None:
        root = build(tmp_path, bodies={"voice": "x" * 8_979})

        assert [kind for kind, _, _ in errors_of(root)] == ["oversize-body"]

    def test_an_oversize_variant_names_its_own_file(self, tmp_path) -> None:
        root = build(tmp_path, stems=["voice"], bodies={"voice@long": "x" * 9_500})

        (error,) = check(root).errors
        assert error.file == root / "rules" / "voice@long.md"


class TestOneRunReportsEveryError:
    def test_a_cycle_an_unknown_fact_and_a_missing_rule_are_all_reported(self, tmp_path) -> None:
        root = build(
            tmp_path,
            "defaults: ghost\nsets:\n  a: b.*\n  b: a.*\nproject amboss:\n  include: voice\n",
            stems=["voice"],
        )

        assert sorted(kind for kind, _, _ in errors_of(root)) == [
            "condition-invalid",
            "ruleset-cycle",
            "undeclared-reference",
        ]

    def test_config_and_rule_file_errors_arrive_in_one_report(self, tmp_path) -> None:
        root = build(tmp_path, "when: x\n", stems=["tone@dry"])

        assert [kind for kind, _, _ in errors_of(root)] == [
            "old-layout",
            "variant-without-default",
        ]


class TestACleanRulesetsDirectory:
    def test_nothing_is_reported(self, tmp_path) -> None:
        root = build(
            tmp_path,
            "models: haiku\n"
            "defaults:\n"
            "  include: all.*\n"
            "  exclude: security\n"
            "sets:\n"
            "  code: voice\n"
            "model haiku:\n"
            "  include: voice@terse\n",
            stems=["voice", "voice@terse", "security"],
        )

        report = check(root)

        assert report.errors == ()

    def test_a_missing_config_reads_as_every_rule_and_is_no_error(self, tmp_path) -> None:
        root = build(tmp_path, stems=["voice"])

        assert errors_of(root) == []

    def test_a_directory_holding_nothing_reports_nothing(self, tmp_path) -> None:
        root = tmp_path / "empty"
        root.mkdir()

        assert check(root).errors == ()


class TestWarningsDoNotCountAsErrors:
    def test_a_stray_directory_is_a_warning_and_leaves_errors_empty(self, tmp_path) -> None:
        root = build(tmp_path, stems=["voice"])
        (root / "rules" / "drafts").mkdir()

        report = check(root)

        assert report.errors == ()
        assert report.warnings
        assert DirectorySubject(root / "rules" / "drafts") in [w.subject for w in report.warnings]
