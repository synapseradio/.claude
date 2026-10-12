#!/usr/bin/env python3
"""Check reports every illegal state of a rulesets directory as an error with its subject.

The check serves the engineer who edits a manifest or a rule file and runs check before
trusting a delivery: each error names its kind, the subject delivery will disable, and the
file and line to open, and one run reports every error together. There is one case per row of
the error table in design.md "Explain and check", plus the cases that must stay silent. Each
case builds its rulesets directory under `tmp_path`.

Run with `python3.14 -m pytest features/rulesets/tests/test_check_errors.py`.
"""

import os
import pathlib
import sys

import pytest

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]

sys.path.insert(0, str(PLUGIN_ROOT / "lib"))

from rulesets.check.findings import (  # noqa: E402
    DirectorySubject,
    ItemSubject,
    KeySubject,
    ManifestSubject,
    ModelSubject,
    ReferencesSubject,
    ReferenceSubject,
    RulesetSubject,
    RuleSubject,
)
from rulesets.check.report_format import finding_line  # noqa: E402
from rulesets.check.run import check  # noqa: E402  (path must be set before this import)


def build(tmp_path, manifest=None, stems=(), bodies=None):
    """A rulesets directory with the manifest text, a file per stem, and any given bodies."""

    root = tmp_path / "rulesets"
    (root / "rules").mkdir(parents=True)
    if manifest is not None:
        (root / "manifest.yaml").write_text(manifest, encoding="utf-8")
    texts = {stem: f"text of {stem}\n" for stem in stems} | (bodies or {})
    for stem, text in texts.items():
        (root / "rules" / f"{stem}.md").write_text(text, encoding="utf-8")
    return root


def errors_of(root):
    return [(error.kind, error.subject, error.line) for error in check(root).errors]


class TestARulesetCycle:
    def test_each_ruleset_declaration_in_the_cycle_is_an_error(self, tmp_path):
        root = build(
            tmp_path,
            "rulesets:\n  a: ['b:*']\n  b: ['a:*']\n  c: ['voice']\n",
            stems=["voice"],
        )

        assert errors_of(root) == [
            ("ruleset-cycle", RulesetSubject("a"), 2),
            ("ruleset-cycle", RulesetSubject("b"), 3),
        ]

    def test_a_ruleset_that_only_spreads_into_a_cycle_is_no_error(self, tmp_path):
        root = build(tmp_path, "rulesets:\n  a: ['b:*']\n  b: ['a:*']\n  c: ['a:*']\n")

        assert [subject for _, subject, _ in errors_of(root)] == [
            RulesetSubject("a"),
            RulesetSubject("b"),
        ]

    def test_a_ruleset_spreading_itself_is_a_cycle(self, tmp_path):
        root = build(tmp_path, "rulesets:\n  a: ['a:*']\n")

        assert errors_of(root) == [("ruleset-cycle", RulesetSubject("a"), 2)]

    def test_a_cycle_through_defaults_names_defaults_and_the_ruleset(self, tmp_path):
        root = build(tmp_path, "defaults: ['a:*']\nrulesets:\n  a: ['defaults:*']\n")

        assert errors_of(root) == [
            ("ruleset-cycle", KeySubject("defaults"), 1),
            ("ruleset-cycle", RulesetSubject("a"), 3),
        ]

    def test_the_message_names_every_ruleset_in_the_cycle(self, tmp_path):
        root = build(tmp_path, "rulesets:\n  a: ['b:*']\n  b: ['a:*']\n")

        message = check(root).errors[0].message
        assert "`a`" in message
        assert "`b`" in message
        assert "cycle" in message

    def test_the_error_names_the_manifest_file(self, tmp_path):
        root = build(tmp_path, "rulesets:\n  a: ['a:*']\n")

        assert check(root).errors[0].file == root / "manifest.yaml"


class TestOneListSettingTwoVariantsOfOneRule:
    def test_the_two_references_are_the_subject(self, tmp_path):
        root = build(
            tmp_path,
            "defaults:\n  - 'voice@terse'\n  - 'voice@warm'\n",
            stems=["voice", "voice@terse", "voice@warm"],
        )

        assert errors_of(root) == [
            (
                "variant-conflict",
                ReferencesSubject(
                    (ReferenceSubject("voice@terse", 2), ReferenceSubject("voice@warm", 3))
                ),
                2,
            )
        ]

    def test_the_conflict_sits_in_a_ruleset_as_well_as_in_defaults(self, tmp_path):
        root = build(
            tmp_path,
            "rulesets:\n  tone: ['voice@terse', 'voice@warm']\n",
            stems=["voice", "voice@terse", "voice@warm"],
        )

        assert [kind for kind, _, _ in errors_of(root)] == ["variant-conflict"]

    def test_the_conflict_sits_in_an_item_list(self, tmp_path):
        root = build(
            tmp_path,
            "when:\n  - flag a: ['voice@terse', 'voice@warm']\n",
            stems=["voice", "voice@terse", "voice@warm"],
        )

        assert [kind for kind, _, _ in errors_of(root)] == ["variant-conflict"]

    def test_two_items_setting_different_variants_are_no_error(self, tmp_path):
        root = build(
            tmp_path,
            "when:\n  - flag voice-terse: ['voice@terse']\n  - flag voice-warm: ['voice@warm']\n",
            stems=["voice", "voice@terse", "voice@warm"],
        )

        assert errors_of(root) == []

    def test_one_variant_named_twice_is_no_conflict(self, tmp_path):
        root = build(
            tmp_path,
            "defaults: ['voice@terse', 'voice@terse']\n",
            stems=["voice", "voice@terse"],
        )

        assert errors_of(root) == []

    def test_a_strike_that_leaves_one_variant_is_no_conflict(self, tmp_path):
        root = build(
            tmp_path,
            "defaults: ['voice@terse', 'voice@warm', '-voice@warm']\n",
            stems=["voice", "voice@terse", "voice@warm"],
        )

        assert errors_of(root) == []


class TestAConditionThatTestsMoreThanFacts:
    def test_a_test_of_a_project_is_an_error_whose_subject_is_the_item(self, tmp_path):
        root = build(tmp_path, "when:\n  - project amboss: ['voice']\n", stems=["voice"])

        assert errors_of(root) == [("condition-invalid", ItemSubject(0), 2)]

    def test_the_message_names_what_the_condition_tests(self, tmp_path):
        root = build(tmp_path, "when:\n  - env CI: ['voice']\n", stems=["voice"])

        assert "env" in check(root).errors[0].message

    def test_text_that_does_not_parse_is_an_error_whose_subject_is_the_item(self, tmp_path):
        root = build(
            tmp_path, "when:\n  - (agent critic and flag strict: ['voice']\n", stems=["voice"]
        )

        assert errors_of(root) == [("condition-invalid", ItemSubject(0), 2)]

    def test_the_item_index_counts_every_item_written(self, tmp_path):
        root = build(
            tmp_path,
            "when:\n  - flag ok: ['voice']\n  - just text\n  - project x: ['voice']\n",
            stems=["voice"],
        )

        assert errors_of(root) == [
            ("item-shape", ItemSubject(1), 3),
            ("condition-invalid", ItemSubject(2), 4),
        ]

    def test_an_agent_nobody_declares_is_no_error(self, tmp_path):
        root = build(tmp_path, "when:\n  - agent eval-runner: ['voice']\n", stems=["voice"])

        assert errors_of(root) == []

    def test_a_flag_nobody_sets_is_no_error(self, tmp_path):
        root = build(tmp_path, "when:\n  - flag stirct: ['voice']\n", stems=["voice"])

        assert errors_of(root) == []

    def test_a_correct_condition_is_no_error(self, tmp_path):
        root = build(
            tmp_path,
            "models: ['haiku']\nwhen:\n  - (agent a or kind fork) and not model haiku: ['voice']\n",
            stems=["voice"],
        )

        assert errors_of(root) == []


class TestAConditionNamingAModelTheManifestDoesNotDeclare:
    def test_the_item_is_the_subject(self, tmp_path):
        root = build(
            tmp_path,
            "models: ['opus']\nwhen:\n  - model hiaku: ['voice']\n",
            stems=["voice"],
        )

        assert errors_of(root) == [("unknown-model", ItemSubject(0), 3)]

    def test_the_message_names_the_model(self, tmp_path):
        root = build(
            tmp_path, "models: ['opus']\nwhen:\n  - model hiaku: ['voice']\n", stems=["voice"]
        )

        assert "hiaku" in check(root).errors[0].message

    def test_a_manifest_declaring_no_models_declares_none(self, tmp_path):
        root = build(tmp_path, "when:\n  - model haiku: ['voice']\n", stems=["voice"])

        assert errors_of(root) == [("unknown-model", ItemSubject(0), 2)]

    def test_a_negated_model_test_is_checked_too(self, tmp_path):
        root = build(
            tmp_path, "models: ['opus']\nwhen:\n  - not model nova: ['voice']\n", stems=["voice"]
        )

        assert errors_of(root) == [("unknown-model", ItemSubject(0), 3)]

    def test_each_undeclared_name_of_one_item_is_named_in_one_error(self, tmp_path):
        root = build(tmp_path, "when:\n  - model nova or model luna: ['voice']\n", stems=["voice"])

        (error,) = check(root).errors
        assert "nova" in error.message
        assert "luna" in error.message

    def test_a_declared_model_is_no_error(self, tmp_path):
        root = build(
            tmp_path, "models: ['opus']\nwhen:\n  - model opus: ['voice']\n", stems=["voice"]
        )

        assert errors_of(root) == []


class TestAWhenItemThatIsNoOneKeyMappingToAList:
    def test_the_item_is_the_subject(self, tmp_path):
        root = build(tmp_path, "when:\n  - flag a: ['voice']\n  - {flag b: x}\n", stems=["voice"])

        assert errors_of(root) == [("item-shape", ItemSubject(1), 3)]

    def test_an_item_whose_value_is_a_mapping_is_named(self, tmp_path):
        root = build(tmp_path, "when:\n  - flag a: {voice: x}\n")

        assert errors_of(root) == [("item-shape", ItemSubject(0), 2)]


class TestAReferenceNamingWhatNothingDeclares:
    def test_an_undeclared_rule_is_an_error_whose_subject_is_the_reference(self, tmp_path):
        root = build(tmp_path, "defaults:\n  - 'voice'\n  - 'ghost'\n", stems=["voice"])

        assert errors_of(root) == [("undeclared-reference", ReferenceSubject("ghost", 3), 3)]

    def test_the_message_names_the_rule(self, tmp_path):
        root = build(tmp_path, "defaults: ['ghost']\n")

        assert "ghost" in check(root).errors[0].message

    def test_the_printed_line_names_the_reference_once_before_the_cause(self, tmp_path):
        root = build(tmp_path, "defaults: ['ghost']\n")

        (error,) = check(root).errors

        assert finding_line(error) == (
            f"{root / 'manifest.yaml'}:1: error [undeclared-reference] "
            "reference `ghost`: the pool holds no rule `ghost`"
        )

    def test_each_cause_is_worded_without_repeating_the_reference(self, tmp_path):
        root = build(
            tmp_path,
            "defaults: ['-rules:ghost', 'voice@loud', 'phantom:*', 'foo:bar']\n",
            stems=["voice"],
        )

        assert [(e.kind, e.message) for e in check(root).errors] == [
            ("undeclared-reference", "the pool holds no rule `ghost`"),
            ("undeclared-reference", "rule `voice` has no variant `loud`"),
            ("undeclared-reference", "no ruleset `phantom` is declared"),
            (
                "malformed-reference",
                "not a reference form; write a rule, rule@variant, rules:rule, or ruleset:*",
            ),
        ]

    def test_an_undeclared_variant_is_an_error(self, tmp_path):
        root = build(tmp_path, "defaults: ['voice@loud']\n", stems=["voice", "voice@terse"])

        assert errors_of(root) == [("undeclared-reference", ReferenceSubject("voice@loud", 1), 1)]

    def test_an_undeclared_ruleset_is_an_error(self, tmp_path):
        root = build(tmp_path, "defaults: ['phantom:*']\n", stems=["voice"])

        assert errors_of(root) == [("undeclared-reference", ReferenceSubject("phantom:*", 1), 1)]

    def test_a_remove_of_an_undeclared_rule_is_an_error(self, tmp_path):
        root = build(tmp_path, "defaults: ['all:*', '-ghost']\n", stems=["voice"])

        assert errors_of(root) == [("undeclared-reference", ReferenceSubject("-ghost", 1), 1)]

    def test_an_undeclared_reference_inside_a_ruleset_and_an_item_is_found(self, tmp_path):
        root = build(
            tmp_path,
            "rulesets:\n  code: ['ghost']\nwhen:\n  - flag a: ['spook']\n",
            stems=["voice"],
        )

        assert errors_of(root) == [
            ("undeclared-reference", ReferenceSubject("ghost", 2), 2),
            ("undeclared-reference", ReferenceSubject("spook", 4), 4),
        ]

    def test_a_reference_reached_by_two_spreads_is_reported_once(self, tmp_path):
        root = build(
            tmp_path,
            "defaults: ['a:*', 'b:*']\nrulesets:\n  a: ['ghost']\n  b: ['a:*']\n",
            stems=["voice"],
        )

        assert errors_of(root) == [("undeclared-reference", ReferenceSubject("ghost", 3), 3)]

    def test_text_that_is_no_reference_form_is_an_error(self, tmp_path):
        root = build(tmp_path, "defaults: ['foo:bar']\n")

        assert errors_of(root) == [("malformed-reference", ReferenceSubject("foo:bar", 1), 1)]

    def test_a_declared_variant_and_ruleset_are_no_error(self, tmp_path):
        root = build(
            tmp_path,
            "defaults: ['voice@terse', 'tone:*']\nrulesets:\n  tone: ['voice']\n",
            stems=["voice", "voice@terse"],
        )

        assert errors_of(root) == []


class TestARulesetWhoseValueIsNotAList:
    def test_the_declaration_is_the_subject(self, tmp_path):
        root = build(tmp_path, "rulesets:\n  code: {a: b}\n  tone: ['voice']\n", stems=["voice"])

        assert errors_of(root) == [("ruleset-shape", RulesetSubject("code"), 2)]


class TestAReservedRulesetDeclared:
    def test_each_reserved_name_is_an_error_naming_the_declaration(self, tmp_path):
        root = build(
            tmp_path,
            "rulesets:\n  defaults: []\n  all: []\n  rules: []\n  none: []\n",
        )

        assert errors_of(root) == [
            ("reserved-ruleset", RulesetSubject("defaults"), 2),
            ("reserved-ruleset", RulesetSubject("all"), 3),
            ("reserved-ruleset", RulesetSubject("rules"), 4),
            ("reserved-ruleset", RulesetSubject("none"), 5),
        ]


class TestARuleWhoseFrontmatterCarriesACondition:
    def test_the_rule_is_the_subject_and_the_condition_line_is_the_line(self, tmp_path):
        root = build(
            tmp_path,
            "defaults: ['voice']\n",
            bodies={"voice": "---\ndescription: tone\nmodel: haiku\n---\ntext\n"},
        )

        (error,) = check(root).errors
        assert (error.kind, error.subject, error.line) == (
            "rule-condition",
            RuleSubject("voice"),
            3,
        )
        assert error.file == root / "rules" / "voice.md"

    def test_a_path_scope_is_a_condition(self, tmp_path):
        root = build(tmp_path, bodies={"voice": "---\npaths:\n  - src/**\n---\ntext\n"})

        assert errors_of(root) == [("rule-condition", RuleSubject("voice"), 2)]

    def test_a_variant_file_carrying_a_condition_names_that_file(self, tmp_path):
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
    def test_each_key_a_condition_can_test_is_a_condition(self, tmp_path, key):
        root = build(tmp_path, bodies={"voice": f"---\n{key}: x\n---\ntext\n"})

        assert errors_of(root) == [("rule-condition", RuleSubject("voice"), 2)]

    def test_the_first_condition_key_in_file_order_is_the_one_named(self, tmp_path):
        root = build(tmp_path, bodies={"voice": "---\ndescription: x\nflags: a\nmodel: b\n---\n"})

        (error,) = check(root).errors
        assert (error.line, "`flags`" in error.message) == (3, True)

    def test_frontmatter_without_a_condition_is_no_error(self, tmp_path):
        root = build(tmp_path, bodies={"voice": "---\ndescription: tone\n---\ntext\n"})

        assert errors_of(root) == []

    def test_frontmatter_that_does_not_parse_is_no_error_and_no_warning(self, tmp_path):
        root = build(tmp_path, bodies={"voice": "---\npaths: [unclosed\n---\ntext\n"})

        report = check(root)

        assert (report.errors, report.warnings) == ((), ())

    def test_a_fence_closed_with_no_trailing_newline_still_carries_a_condition(self, tmp_path):
        root = build(tmp_path)
        (root / "rules" / "voice.md").write_bytes(b"---\r\nmodel: haiku\r\n---")

        assert errors_of(root) == [("rule-condition", RuleSubject("voice"), 2)]


class TestAVariantBesideNoDefaultForm:
    def test_the_rule_is_the_subject(self, tmp_path):
        root = build(tmp_path, stems=["tone@dry"])

        (error,) = check(root).errors
        assert (error.kind, error.subject) == ("variant-without-default", RuleSubject("tone"))
        assert error.file == root / "rules" / "tone@dry.md"

    def test_a_variant_beside_its_default_is_no_error(self, tmp_path):
        root = build(tmp_path, stems=["tone", "tone@dry"])

        assert errors_of(root) == []


class TestARuleFileThatCannotBeRead:
    def test_a_file_that_is_not_utf8_is_an_error_whose_subject_is_the_rule(self, tmp_path):
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

    def test_the_unreadable_file_draws_no_other_finding(self, tmp_path):
        root = build(tmp_path)
        (root / "rules" / "voice.md").write_bytes(b"\xff\xfe")

        report = check(root)

        assert [error.kind for error in report.errors] == ["unreadable-file"]
        assert report.warnings == ()

    def test_every_unreadable_file_of_a_rule_is_reported(self, tmp_path):
        root = build(tmp_path)
        (root / "rules" / "voice.md").write_bytes(b"\xff")
        (root / "rules" / "voice@terse.md").write_bytes(b"\xfe")

        assert [(kind, subject) for kind, subject, _ in errors_of(root)] == [
            ("unreadable-file", RuleSubject("voice")),
            ("unreadable-file", RuleSubject("voice")),
        ]

    def test_the_other_errors_of_the_run_still_arrive(self, tmp_path):
        root = build(tmp_path, "project: x\n")
        (root / "rules" / "voice.md").write_bytes(b"\xff")

        assert [kind for kind, _, _ in errors_of(root)] == ["unknown-key", "unreadable-file"]


class TestATopLevelKeyOtherThanTheFour:
    def test_the_key_is_the_subject(self, tmp_path):
        root = build(tmp_path, "defaults: ['voice']\nproject: amboss\n", stems=["voice"])

        assert errors_of(root) == [("unknown-key", KeySubject("project"), 2)]


class TestEveryManifestShapeErrorIsWordedForTheFileToOpen:
    def test_each_kind_names_the_manifest_file_and_says_what_is_wrong(self, tmp_path):
        text = (
            "project: x\n"
            "models: opus\n"
            "rulesets:\n"
            "  code: {a: b}\n"
            "  all: []\n"
            "when:\n"
            "  - just a string\n"
        )
        root = build(tmp_path, text)

        errors = check(root).errors

        assert {error.file for error in errors} == {root / "manifest.yaml"}
        assert [(error.kind, error.message) for error in errors] == [
            (
                "unknown-key",
                "`project` is not a manifest key; the keys are models, defaults, rulesets, and when",
            ),
            ("key-shape", "`models` must be a list of model names"),
            ("ruleset-shape", "ruleset `code` must be a list of references"),
            ("reserved-ruleset", "`all` is a reserved ruleset and cannot be declared"),
            (
                "item-shape",
                "an item must be a one-key mapping from a condition to a list of references",
            ),
        ]


class TestATopLevelValueOfTheWrongShape:
    def test_defaults_holding_a_mapping_names_the_key(self, tmp_path):
        root = build(tmp_path, "defaults:\n  all: true\n")

        assert errors_of(root) == [("key-shape", KeySubject("defaults"), 1)]

    def test_each_of_the_four_keys_has_a_shape(self, tmp_path):
        root = build(
            tmp_path,
            "models: opus\ndefaults: all:*\nrulesets: [code]\nwhen: {flag a: [voice]}\n",
        )

        assert errors_of(root) == [
            ("key-shape", KeySubject("models"), 1),
            ("key-shape", KeySubject("defaults"), 2),
            ("key-shape", KeySubject("rulesets"), 3),
            ("key-shape", KeySubject("when"), 4),
        ]


class TestAManifestThatDoesNotParse:
    def test_an_unquoted_model_name_holding_brackets_is_an_error_at_its_line(self, tmp_path):
        root = build(tmp_path, "defaults: [voice]\nmodels: [opus, opus-4-8[1m]]\n", stems=["voice"])

        (error,) = check(root).errors
        assert (error.kind, error.subject, error.line) == (
            "manifest-unparsable",
            ManifestSubject(),
            2,
        )
        assert error.file == root / "manifest.yaml"

    def test_a_manifest_that_is_not_utf8_is_unparsable_and_names_the_cause_and_line(self, tmp_path):
        root = build(tmp_path)
        (root / "manifest.yaml").write_bytes(b"defaults: [all:*]\nmodels: [\xff]\n")

        (error,) = check(root).errors

        assert (error.kind, error.subject, error.line) == (
            "manifest-unparsable",
            ManifestSubject(),
            2,
        )
        assert error.file == root / "manifest.yaml"
        assert "UTF-8" in error.message

    def test_a_manifest_decode_error_far_into_the_file_names_its_line(self, tmp_path):
        root = build(tmp_path)
        filler = b"# padding\n" * 2000
        (root / "manifest.yaml").write_bytes(filler + b"models: [\xff]\n")

        (error,) = check(root).errors

        assert (error.kind, error.line) == ("manifest-unparsable", 2001)

    @pytest.mark.skipif(os.geteuid() == 0, reason="root reads a file whatever its mode")
    def test_a_manifest_the_system_cannot_open_is_unparsable_with_no_line(self, tmp_path):
        root = build(tmp_path)
        (root / "manifest.yaml").write_text("defaults: ['all:*']\n", encoding="utf-8")
        (root / "manifest.yaml").chmod(0)

        (error,) = check(root).errors

        assert (error.kind, error.subject, error.line) == (
            "manifest-unparsable",
            ManifestSubject(),
            None,
        )
        assert error.message

    def test_the_quoted_name_is_no_error(self, tmp_path):
        root = build(tmp_path, 'models: ["opus", "opus-4-8[1m]"]\n')

        assert errors_of(root) == []

    def test_rule_file_errors_are_still_reported(self, tmp_path):
        root = build(tmp_path, "models: [opus-4-8[1m]]\n", stems=["tone@dry"])

        assert [kind for kind, _, _ in errors_of(root)] == [
            "manifest-unparsable",
            "variant-without-default",
        ]


class TestAListEntryThatIsNotAQuotedString:
    def test_a_plain_reference_is_an_error_whose_subject_is_the_reference(self, tmp_path):
        root = build(tmp_path, "defaults: [all:*]\n", stems=["voice"])

        assert errors_of(root) == [("unquoted-entry", ReferenceSubject("all:*", 1), 1)]

    def test_the_message_says_how_to_write_the_entry(self, tmp_path):
        root = build(tmp_path, "defaults: [all:*]\n", stems=["voice"])

        (error,) = check(root).errors

        assert error.message == (
            "`all:*` is not quoted; write every list entry as a quoted string, `'all:*'`"
        )
        assert finding_line(error).endswith(
            "reference `all:*`: `all:*` is not quoted; "
            "write every list entry as a quoted string, `'all:*'`"
        )

    def test_the_reference_is_skipped_like_one_nothing_declares(self, tmp_path):
        root = build(tmp_path, "defaults: [voice, 'sorting']\n", stems=["voice", "sorting"])

        (error,) = check(root).errors
        warnings = [(w.kind, w.subject) for w in check(root).warnings]

        assert error.kind == "unquoted-entry"
        assert ("never-included", RuleSubject("voice")) in warnings
        assert ("never-included", RuleSubject("sorting")) not in warnings

    @pytest.mark.parametrize(
        ("entry", "subject", "message"),
        [
            (
                "2024",
                "2024",
                "`2024` is not quoted; write every list entry as a quoted string, `'2024'`",
            ),
            ("~", "~", "`~` is not quoted; write every list entry as a quoted string, `'~'`"),
            (
                "{a: b}",
                "{a: b}",
                "`{a: b}` is a mapping; write every list entry as a quoted string",
            ),
            (
                "[a, b]",
                "[a, b]",
                "`[a, b]` is a list; write every list entry as a quoted string",
            ),
        ],
    )
    def test_each_unquoted_shape_is_worded_for_what_it_is(self, tmp_path, entry, subject, message):
        root = build(tmp_path, f"defaults: [{entry}]\n")

        (error,) = check(root).errors

        assert (error.kind, error.subject, error.message) == (
            "unquoted-entry",
            ReferenceSubject(subject, 1),
            message,
        )

    def test_an_empty_entry_is_an_error(self, tmp_path):
        root = build(tmp_path, "defaults:\n  - \n  - 'voice'\n", stems=["voice"])

        (error,) = check(root).errors

        assert (error.kind, error.line) == ("unquoted-entry", 2)
        assert (
            error.message
            == "an empty entry is not a quoted string; write every list entry as a quoted string"
        )

    def test_a_mapping_typo_inside_a_flow_list_is_one_error_for_the_entry(self, tmp_path):
        root = build(tmp_path, "defaults: ['voice', a: b]\n", stems=["voice"])

        assert errors_of(root) == [("unquoted-entry", ReferenceSubject("a: b", 1), 1)]

    def test_both_quote_styles_are_legal(self, tmp_path):
        root = build(tmp_path, "defaults: ['voice', \"sorting\"]\n", stems=["voice", "sorting"])

        assert errors_of(root) == []

    def test_every_list_is_held_to_it(self, tmp_path):
        manifest = "defaults: [a]\nrulesets:\n  code: [b]\nwhen:\n  - flag x: [c]\n"
        root = build(tmp_path, manifest)

        assert errors_of(root) == [
            ("unquoted-entry", ReferenceSubject("a", 1), 1),
            ("unquoted-entry", ReferenceSubject("b", 3), 3),
            ("unquoted-entry", ReferenceSubject("c", 5), 5),
        ]

    def test_a_when_condition_stays_unquoted_and_may_be_quoted(self, tmp_path):
        manifest = "when:\n  - flag a: ['voice']\n  - 'flag b': ['voice']\n"
        root = build(tmp_path, manifest, stems=["voice"])

        assert errors_of(root) == []

    def test_a_model_entry_is_an_error_whose_subject_is_the_entry_and_the_name_is_undeclared(
        self, tmp_path
    ):
        manifest = "models: [opus, 'sonnet']\nwhen:\n  - model opus: ['voice']\n"
        root = build(tmp_path, manifest, stems=["voice"])

        assert errors_of(root) == [
            ("unquoted-entry", ModelSubject("opus"), 1),
            ("unknown-model", ItemSubject(0), 3),
        ]

    def test_a_model_entry_that_is_a_number_is_the_same_error(self, tmp_path):
        root = build(tmp_path, "models: ['opus', 5]\n")

        assert errors_of(root) == [("unquoted-entry", ModelSubject("5"), 1)]

    def test_a_models_value_that_is_no_list_stays_a_key_shape_error(self, tmp_path):
        root = build(tmp_path, "models: opus\n")

        assert errors_of(root) == [("key-shape", KeySubject("models"), 1)]

    def test_a_model_error_is_worded_for_the_model(self, tmp_path):
        root = build(tmp_path, "models: [opus]\n")

        (error,) = check(root).errors

        assert finding_line(error).endswith(
            "model `opus`: `opus` is not quoted; write every list entry as a quoted string, `'opus'`"
        )


class TestAManifestThatCannotParseBecauseOfAnUnquotedEntry:
    @pytest.mark.parametrize(
        "text",
        [
            "defaults: [*]\n",
            "defaults: [*foo]\n",
            "models: [opus, opus-4-8[1m]]\n",
        ],
    )
    def test_the_message_advises_quoting_every_list_entry(self, tmp_path, text):
        root = build(tmp_path, text)

        (error,) = check(root).errors

        assert error.kind == "manifest-unparsable"
        assert error.message.endswith("; write every list entry as a quoted string")

    def test_a_parse_failure_with_another_cause_carries_no_advice(self, tmp_path):
        root = build(tmp_path, "defaults: 'unterminated\n")

        (error,) = check(root).errors

        assert error.kind == "manifest-unparsable"
        assert "quoted string" not in error.message


class TestOneRunReportsEveryError:
    def test_a_cycle_an_unknown_fact_and_a_missing_rule_are_all_reported(self, tmp_path):
        root = build(
            tmp_path,
            "defaults: ['ghost']\n"
            "rulesets:\n"
            "  a: ['b:*']\n"
            "  b: ['a:*']\n"
            "when:\n"
            "  - project amboss: ['voice']\n",
            stems=["voice"],
        )

        assert sorted(kind for kind, _, _ in errors_of(root)) == [
            "condition-invalid",
            "ruleset-cycle",
            "ruleset-cycle",
            "undeclared-reference",
        ]

    def test_manifest_and_rule_file_errors_arrive_in_one_report(self, tmp_path):
        root = build(tmp_path, "project: x\n", stems=["tone@dry"])

        assert [kind for kind, _, _ in errors_of(root)] == [
            "unknown-key",
            "variant-without-default",
        ]


class TestACleanRulesetsDirectory:
    def test_nothing_is_reported(self, tmp_path):
        root = build(
            tmp_path,
            "models: ['haiku']\n"
            "defaults: ['all:*', '-security']\n"
            "rulesets:\n"
            "  code: ['voice']\n"
            "when:\n"
            "  - model haiku: ['voice@terse']\n",
            stems=["voice", "voice@terse", "security"],
        )

        report = check(root)

        assert report.errors == ()

    def test_a_missing_manifest_reads_as_every_rule_and_is_no_error(self, tmp_path):
        root = build(tmp_path, stems=["voice"])

        assert errors_of(root) == []

    def test_a_directory_holding_nothing_reports_nothing(self, tmp_path):
        root = tmp_path / "empty"
        root.mkdir()

        assert check(root).errors == ()


class TestWarningsDoNotCountAsErrors:
    def test_a_stray_directory_is_a_warning_and_leaves_errors_empty(self, tmp_path):
        root = build(tmp_path, stems=["voice"])
        (root / "rules" / "drafts").mkdir()

        report = check(root)

        assert report.errors == ()
        assert report.warnings
        assert DirectorySubject(root / "rules" / "drafts") in [w.subject for w in report.warnings]
