#!/usr/bin/env python3
"""Explain and check tell a rule author what the engine will deliver and what it will not.

Serves the rule author who asks why an agent did or did not receive a rule, and who runs check
before trusting a delivery. Each case builds its rulesets directory under `tmp_path`, runs the
`explain` or `check` subcommand as a script, or a hook delivery, as a person and the harness do,
and reads what they print or receive. Expected values come from the specs and the fixture files,
never from the engine's own composition.

Run with `python3.14 -m pytest features/plugins/rulesets/tests/test_composition_explain.py`.
"""

import pathlib
import re
import subprocess
import sys
from typing import NamedTuple

import pytest
from delivery_world import DECLARED, World

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]
CLI = PLUGIN_ROOT / "lib" / "rulesets" / "cli.py"

sys.path.insert(0, str(PLUGIN_ROOT / "lib"))

from rulesets.check.cross_reference_check import (  # noqa: E402  (path must be set before this import)
    cross_reference_warnings,
)
from rulesets.compose.composition import compose  # noqa: E402
from rulesets.facts.context import ABSENT, Facts  # noqa: E402
from rulesets.session.state import SessionState  # noqa: E402
from rulesets.source.directory import read_directory  # noqa: E402


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


def explain(root, rule, *options):
    return subprocess.run(
        [sys.executable, str(CLI), "explain", rule, "--root", str(root), *options],
        capture_output=True,
        text=True,
        check=False,
        cwd=CLI.parent,
    )


def check(root):
    return subprocess.run(
        [sys.executable, str(CLI), "check", "--root", str(root)],
        capture_output=True,
        text=True,
        check=False,
        cwd=CLI.parent,
    )


class Finding(NamedTuple):
    file: str
    line: int | None
    severity: str
    kind: str
    message: str


_FINDING = re.compile(
    r"(?P<file>.+?)(?::(?P<line>\d+))?: (?P<severity>error|warning) \[(?P<kind>[^\]]+)\] (?P<message>.*)"
)


def findings(result):
    """Each line check printed as its file, line, severity, kind, and message."""

    found = []
    for text in result.stdout.splitlines():
        parts = _FINDING.fullmatch(text)
        assert parts, f"not a finding line: {text!r}"
        line = parts["line"]
        found.append(
            Finding(
                parts["file"],
                int(line) if line else None,
                parts["severity"],
                parts["kind"],
                parts["message"],
            )
        )
    return found


def attribute(result, name):
    """The rows printed under the attribute `name`, each as its cells.

    A cell ends where two or more spaces begin. The attribute's own header line is the first cell
    row's predecessor and is not returned; use `header` for it.
    """

    rows: list[list[str]] = []
    inside = False
    for line in result.stdout.splitlines():
        if not line.startswith(" "):
            inside = line.startswith(f"{name}:")
            continue
        if inside:
            rows.append(re.split(r"\s{2,}", line.strip()))
    return rows


def header(result, name):
    """The line that opens the attribute `name`, or None where the output has none."""

    return next(
        (line for line in result.stdout.splitlines() if line.startswith(f"{name}:")),
        None,
    )


class TestExplainTracesOneRuleInOneContext:
    def test_lines_of_named_facts_are_listed_and_lines_of_unnamed_facts_are_not(self, tmp_path):
        root = build(
            tmp_path,
            "models: ['haiku']\n"
            "flags: ['strict']\n"
            "when:\n"
            "  - not flag strict: ['voice']\n"
            "  - not agent eval-runner: ['-voice']\n",
            ["voice"],
        )

        result = explain(root, "voice", "--model", "haiku")

        assert result.returncode == 0
        conditions = [row[2] for row in attribute(result, "inclusion")]
        assert conditions == ["not flag strict"]
        assert "not agent eval-runner" not in result.stdout

    def test_a_kind_left_unnamed_is_unknown_so_a_block_testing_its_negation_does_not_apply(
        self, tmp_path
    ):
        root = build(
            tmp_path,
            "defaults: ['voice']\nwhen:\n  - not kind delegate: ['-voice']\n",
            ["voice"],
        )

        unnamed = explain(root, "voice")
        named = explain(root, "voice", "--kind", "session")

        assert [row[2] for row in attribute(unnamed, "inclusion")] == ["defaults"]
        assert [row[2] for row in attribute(named, "inclusion")] == [
            "not kind delegate",
            "defaults",
        ]


class TestExplainPrintsInclusionAndVariantEachOpeningWithTheWinner:
    def test_each_attribute_opens_with_its_winner_and_lists_the_lines_it_beat(self, tmp_path):
        root = build(
            tmp_path,
            "models: ['haiku']\n"
            "defaults: ['writing-prose']\n"
            "when:\n"
            "  - model haiku: ['writing-prose@haiku']\n"
            "  - agent eval-runner: ['-writing-prose']\n",
            ["writing-prose", "writing-prose@haiku"],
        )
        manifest = f"{root}/manifest.yaml"

        result = explain(root, "writing-prose", "--model", "haiku", "--agent", "eval-runner")

        assert result.returncode == 0
        assert attribute(result, "inclusion") == [
            ["wins", f"{manifest}:5", "agent eval-runner", "-writing-prose", "names the rule"],
            ["beat", f"{manifest}:2", "defaults", "writing-prose", "names the rule"],
            ["beat", f"{manifest}:4", "model haiku", "writing-prose@haiku", "names the rule"],
        ]
        assert header(result, "inclusion") == "inclusion: off"
        assert header(result, "variant") == "variant: haiku"
        assert attribute(result, "variant") == [
            ["wins", f"{manifest}:4", "model haiku", "writing-prose@haiku", "names the rule"],
        ]
        assert "rank" not in result.stdout.lower()

    def test_a_block_that_does_not_apply_is_absent_from_the_output(self, tmp_path):
        root = build(
            tmp_path,
            "models: ['opus', 'haiku']\n"
            "defaults: ['writing-code']\n"
            "when:\n"
            "  - model haiku: ['-writing-code']\n",
            ["writing-code"],
        )

        result = explain(root, "writing-code", "--model", "opus")

        assert [row[2] for row in attribute(result, "inclusion")] == ["defaults"]
        assert "model haiku" not in result.stdout
        assert "-writing-code" not in result.stdout


class TestEachLineGivesItsSourceAndReach:
    def test_a_line_reaching_the_rule_through_a_ruleset_names_the_ruleset(self, tmp_path):
        root = build(
            tmp_path,
            "models: ['haiku']\n"
            "rulesets:\n"
            "  reviewer: ['report-format']\n"
            "when:\n"
            "  - model haiku: ['reviewer:*']\n",
            ["report-format"],
        )

        result = explain(root, "report-format", "--model", "haiku")

        assert attribute(result, "inclusion") == [
            [
                "wins",
                f"{root}/manifest.yaml:5",
                "model haiku",
                "reviewer:*",
                "through ruleset reviewer",
            ]
        ]

    def test_a_line_reaching_the_rule_through_nested_rulesets_names_the_chain_down_to_the_holder(
        self, tmp_path
    ):
        root = build(
            tmp_path,
            "rulesets:\n  outer: ['inner:*']\n  inner: ['voice']\ndefaults: ['outer:*']\n",
            ["voice"],
        )

        result = explain(root, "voice")

        assert attribute(result, "inclusion") == [
            [
                "wins",
                f"{root}/manifest.yaml:4",
                "defaults",
                "outer:*",
                "through ruleset outer > inner",
            ]
        ]

    def test_a_chain_of_three_rulesets_names_each_from_the_spread_one_down(self, tmp_path):
        root = build(
            tmp_path,
            "rulesets:\n"
            "  top: ['middle:*', 'sorting']\n"
            "  middle: ['bottom:*']\n"
            "  bottom: ['voice']\n"
            "defaults: ['top:*']\n",
            ["voice", "sorting"],
        )

        result = explain(root, "voice")

        assert [row[4] for row in attribute(result, "inclusion")] == [
            "through ruleset top > middle > bottom"
        ]


class TestExplainPlacesEachLineUnderInclusionVariantOrBoth:
    def test_a_bare_add_and_a_bare_remove_appear_under_inclusion_only(self, tmp_path):
        root = build(
            tmp_path,
            "flags: ['a', 'b']\nwhen:\n  - flag a: ['voice']\n  - flag b: ['-sorting']\n",
            ["voice", "sorting"],
        )

        added = explain(root, "voice", "--flag", "a", "--flag", "b")
        removed = explain(root, "sorting", "--flag", "a", "--flag", "b")

        assert [row[3] for row in attribute(added, "inclusion")] == ["voice"]
        assert header(added, "variant") is not None
        assert attribute(added, "variant") == []
        assert [row[3] for row in attribute(removed, "inclusion")] == ["-sorting"]
        assert header(removed, "variant") is not None
        assert attribute(removed, "variant") == []

    def test_an_add_at_a_variant_appears_under_inclusion_and_under_variant(self, tmp_path):
        root = build(
            tmp_path,
            "flags: ['a']\nwhen:\n  - flag a: ['voice@terse']\n",
            ["voice", "voice@terse"],
        )

        result = explain(root, "voice", "--flag", "a")

        assert [row[3] for row in attribute(result, "inclusion")] == ["voice@terse"]
        assert [row[3] for row in attribute(result, "variant")] == ["voice@terse"]

    def test_a_strike_appears_under_variant_only(self, tmp_path):
        root = build(
            tmp_path,
            "flags: ['a']\nwhen:\n  - flag a: ['-voice@terse']\n",
            ["voice", "voice@terse"],
        )

        result = explain(root, "voice", "--flag", "a")

        assert header(result, "inclusion") is not None
        assert attribute(result, "inclusion") == []
        assert [row[3] for row in attribute(result, "variant")] == ["-voice@terse"]


class TestExplainStatesWhatNoLineSays:
    def test_a_flag_keyed_variant_leads_with_the_flag_and_the_default_form_is_stated_without_it(
        self, tmp_path
    ):
        root = build(
            tmp_path,
            "flags: ['voice-terse']\n"
            "defaults: ['voice']\n"
            "when:\n"
            "  - flag voice-terse: ['voice@terse']\n",
            ["voice", "voice@terse"],
        )

        flagged = explain(root, "voice", "--flag", "voice-terse")
        unflagged = explain(root, "voice")

        assert header(flagged, "variant") == "variant: terse"
        assert attribute(flagged, "variant")[0][:3] == [
            "wins",
            f"{root}/manifest.yaml:4",
            "flag voice-terse",
        ]
        assert "the default form is delivered" in header(unflagged, "variant")
        assert header(unflagged, "variant") is not None
        assert attribute(unflagged, "variant") == []

    def test_a_rule_no_applying_line_includes_is_reported_as_never_reached(self, tmp_path):
        root = build(
            tmp_path,
            "defaults: ['sorting']\nwhen:\n  - agent writer: ['voice']\n",
            ["sorting", "voice"],
        )

        result = explain(root, "voice", "--agent", "critic")

        assert result.returncode == 0
        assert header(result, "inclusion") == (
            "inclusion: no list reaches the rule in this context"
        )

    def test_a_rule_that_is_excluded_or_unreached_is_not_said_to_deliver_its_default_form(
        self, tmp_path
    ):
        root = build(
            tmp_path,
            "defaults: ['voice', '-voice']\n",
            ["voice", "sorting"],
        )

        excluded = explain(root, "voice")
        unreached = explain(root, "sorting")

        assert header(excluded, "inclusion") == "inclusion: off"
        assert header(excluded, "variant") == "variant: none set"
        assert header(unreached, "inclusion") == (
            "inclusion: no list reaches the rule in this context"
        )
        assert header(unreached, "variant") == "variant: none set"
        assert "default form is delivered" not in excluded.stdout
        assert "default form is delivered" not in unreached.stdout

    def test_an_included_rule_that_is_withheld_is_not_said_to_deliver_its_default_form(
        self, tmp_path
    ):
        root = build(
            tmp_path,
            "defaults: ['big']\n",
            bodies={"big": "x" * 9001},
        )

        result = explain(root, "big")

        assert header(result, "inclusion") == "inclusion: on"
        assert header(result, "variant") == "variant: none set"
        assert "default form is delivered" not in result.stdout
        assert any(line.startswith("withheld:") for line in result.stdout.splitlines())

    def test_a_rule_with_only_a_variant_file_is_stated_as_withheld_with_its_error(self, tmp_path):
        root = build(tmp_path, None, bodies={"tone@dry": "dry tone\n"})

        result = explain(root, "tone")

        withheld = next(line for line in result.stdout.splitlines() if line.startswith("withheld:"))
        assert "`tone` is withheld" in withheld
        assert "variant `dry` and no default form" in withheld


class TestExplainLabelsEachVariantLineByWhatItDid:
    def test_a_strike_above_the_winner_strikes_and_the_add_it_removed_is_struck_not_beaten(
        self, tmp_path
    ):
        root = build(
            tmp_path,
            "flags: ['f']\n"
            "models: ['opus']\n"
            "defaults: ['voice@dry']\n"
            "when:\n"
            "  - model opus: ['voice@terse']\n"
            "  - flag f: ['-voice@terse']\n",
            ["voice", "voice@dry", "voice@terse"],
        )
        manifest = f"{root}/manifest.yaml"

        result = explain(root, "voice", "--model", "opus", "--flag", "f")

        assert header(result, "variant") == "variant: dry"
        assert attribute(result, "variant") == [
            ["wins", f"{manifest}:3", "defaults", "voice@dry", "names the rule"],
            ["struck", f"{manifest}:5", "model opus", "voice@terse", "names the rule"],
            ["strikes", f"{manifest}:6", "flag f", "-voice@terse", "names the rule"],
        ]

    def test_an_add_the_winner_outranked_is_beaten_and_a_strike_of_another_variant_strikes(
        self, tmp_path
    ):
        root = build(
            tmp_path,
            "flags: ['f']\n"
            "models: ['opus']\n"
            "defaults: ['voice@dry']\n"
            "when:\n"
            "  - model opus: ['voice@terse']\n"
            "  - flag f: ['-voice@plain']\n",
            ["voice", "voice@dry", "voice@terse", "voice@plain"],
        )
        manifest = f"{root}/manifest.yaml"

        result = explain(root, "voice", "--model", "opus", "--flag", "f")

        assert header(result, "variant") == "variant: terse"
        assert attribute(result, "variant") == [
            ["wins", f"{manifest}:5", "model opus", "voice@terse", "names the rule"],
            ["beat", f"{manifest}:3", "defaults", "voice@dry", "names the rule"],
            ["strikes", f"{manifest}:6", "flag f", "-voice@plain", "names the rule"],
        ]


class TestExplainNamesAConflictAndTheVariantDeliveryTakes:
    def test_both_conflicting_lines_are_listed_with_the_variant_delivery_takes(self, tmp_path):
        manifest = (
            "flags: ['a', 'b']\n"
            "defaults: ['voice@plain']\n"
            "when:\n"
            "  - flag a: ['voice@terse']\n"
            "  - flag b: ['voice@dry']\n"
        )
        root = build(tmp_path, manifest, ["voice", "voice@plain", "voice@terse", "voice@dry"])

        result = explain(root, "voice", "--flag", "a", "--flag", "b")

        file = f"{root}/manifest.yaml"
        rows = attribute(result, "variant")
        assert [row[:3] for row in rows[:3]] == [
            ["wins", f"{file}:2", "defaults"],
            ["conflict", f"{file}:4", "flag a"],
            ["conflict", f"{file}:5", "flag b"],
        ]
        assert rows[3] == [
            "conflict: `voice@terse` and `voice@dry` set different variants at one position; "
            "delivery takes plain"
        ]
        delivered = compose(
            read_directory(root),
            Facts(ABSENT, ABSENT, ABSENT, frozenset({"a", "b"})),
            SessionState(),
        )
        assert [d.variant for d in delivered.rules] == ["plain"]


class TestExplainExitsNonZeroOnAnUnknownRule:
    def test_a_name_the_pool_does_not_hold_fails_and_is_named(self, tmp_path):
        root = build(tmp_path, "defaults: ['voice']\n", ["voice"])

        result = explain(root, "no-such-rule")

        assert result.returncode == 1
        assert "no-such-rule" in result.stderr
        assert "Traceback" not in result.stderr


class TestCheckReportsEveryErrorAndWarningInOneRun:
    def test_a_cycle_a_bad_condition_and_a_missing_rule_are_all_reported_with_file_and_line(
        self, tmp_path
    ):
        root = build(
            tmp_path,
            "defaults: ['ghost']\n"
            "rulesets:\n"
            "  a: ['b:*']\n"
            "  b: ['a:*']\n"
            "when:\n"
            "  - project amboss: ['voice']\n",
            ["voice"],
        )
        manifest = str(root / "manifest.yaml")

        result = check(root)

        assert result.returncode != 0
        found = findings(result)
        assert sorted((f.file, f.line, f.severity, f.kind) for f in found) == [
            (manifest, 1, "error", "undeclared-reference"),
            (manifest, 3, "error", "ruleset-cycle"),
            (manifest, 6, "error", "condition-invalid"),
        ]
        by_line = {f.line: f.message for f in found}
        assert "ghost" in by_line[1]
        assert "project" in by_line[6]

    def test_a_cycle_is_one_error_whose_subject_is_every_ruleset_in_it_at_the_first_one_written(
        self, tmp_path
    ):
        root = build(
            tmp_path,
            "defaults: ['c:*']\n"
            "rulesets:\n"
            "  a: ['b:*']\n"
            "  b: ['c:*']\n"
            "  c: ['a:*', 'voice']\n"
            "  d: ['a:*']\n",
            ["voice"],
        )

        result = check(root)

        (found,) = findings(result)
        assert (found.file, found.line) == (str(root / "manifest.yaml"), 3)
        assert (found.severity, found.kind) == ("error", "ruleset-cycle")
        assert found.message.startswith("rulesets `a`, `b`, and `c`:")
        assert "`d`" not in found.message

    def test_warnings_alone_are_reported_with_file_and_line_and_the_exit_status_is_zero(
        self, tmp_path
    ):
        root = build(
            tmp_path,
            "defaults: ['report-format']\n",
            ["sorting"],
            {"report-format": "Follow sorting before you list items\n"},
        )

        result = check(root)

        assert result.returncode == 0
        by_kind = {f.kind: f for f in findings(result)}
        assert sorted(by_kind) == ["cross-reference", "never-included"]
        assert {f.severity for f in by_kind.values()} == {"warning"}
        assert by_kind["never-included"].file == str(root / "rules" / "sorting.md")
        assert "`sorting`" in by_kind["never-included"].message
        assert (by_kind["cross-reference"].file, by_kind["cross-reference"].line) == (
            str(root / "rules" / "report-format.md"),
            1,
        )

    def test_a_directory_with_no_error_and_no_warning_prints_nothing_and_exits_zero(self, tmp_path):
        root = build(tmp_path, "defaults: ['all:*']\n", ["voice", "sorting"])

        result = check(root)

        assert (result.returncode, result.stdout, result.stderr) == (0, "", "")


class TestCheckWarnsOfARuleNoAddIncludes:
    def test_a_rule_included_only_by_a_block_keyed_on_a_flag_never_set_draws_no_warning(
        self, tmp_path
    ):
        root = build(
            tmp_path,
            "flags: ['never-set']\nwhen:\n  - flag never-set: ['voice']\n",
            ["voice"],
        )

        result = check(root)

        assert (result.returncode, result.stdout) == (0, "")

    def test_a_rule_added_by_two_conflicting_variant_adds_draws_the_conflict_and_no_warning(
        self, tmp_path
    ):
        root = build(
            tmp_path,
            "defaults: ['voice@a', 'voice@b']\n",
            ["voice", "voice@a", "voice@b"],
        )

        result = check(root)

        assert result.returncode != 0
        (finding,) = findings(result)
        assert (finding.file, finding.line) == (str(root / "manifest.yaml"), 1)
        assert (finding.severity, finding.kind) == ("error", "variant-conflict")

    def test_a_rule_only_a_ruleset_nothing_spreads_lists_draws_no_warning(self, tmp_path):
        root = build(
            tmp_path,
            "defaults: ['sorting']\nrulesets:\n  team: ['voice']\n",
            ["voice", "sorting"],
        )

        result = check(root)

        assert (result.returncode, result.stdout) == (0, "")

    def test_a_rule_that_defaults_removes_and_no_list_adds_draws_a_warning_naming_rule_and_file(
        self, tmp_path
    ):
        root = build(tmp_path, "defaults: ['voice', '-sorting']\n", ["voice", "sorting"])

        result = check(root)

        assert result.returncode == 0
        (finding,) = findings(result)
        assert finding.severity == "warning"
        assert finding.kind == "never-included"
        assert finding.file == str(root / "rules" / "sorting.md")
        assert "`sorting`" in finding.message


class TestCheckReportsAnErrorForEachIllegalDeclarationReferenceOrCycle:
    def test_an_unknown_top_level_key_is_an_error_naming_the_key(self, tmp_path):
        root = build(tmp_path, "defaults: ['voice']\nproject: amboss\n", ["voice"])

        result = check(root)

        assert result.returncode != 0
        (finding,) = findings(result)
        assert (finding.file, finding.line) == (str(root / "manifest.yaml"), 2)
        assert (finding.severity, finding.kind) == ("error", "unknown-key")
        assert "`project`" in finding.message


class TestCheckReportsAnErrorForEachIllegalBlock:
    def test_a_block_whose_value_is_a_mapping_is_an_error_naming_the_block(self, tmp_path):
        root = build(
            tmp_path,
            "models: ['opus']\n"
            "flags: ['f']\n"
            "when:\n"
            "  - flag f: ['voice']\n"
            "  - model opus: {rule: voice}\n",
            ["voice"],
        )

        result = check(root)

        assert result.returncode != 0
        (finding,) = [f for f in findings(result) if f.severity == "error"]
        assert (finding.file, finding.line) == (str(root / "manifest.yaml"), 5)
        assert (finding.severity, finding.kind) == ("error", "item-shape")
        assert finding.message.startswith("item 2:")
        assert "`model opus`" in finding.message

    def test_an_item_with_no_single_condition_is_named_by_its_position(self, tmp_path):
        root = build(
            tmp_path,
            "flags: ['f']\nwhen:\n  - flag f: ['voice']\n  - just text\n",
            ["voice"],
        )

        result = check(root)

        (finding,) = [f for f in findings(result) if f.severity == "error"]
        assert (finding.file, finding.line) == (str(root / "manifest.yaml"), 4)
        assert (finding.severity, finding.kind) == ("error", "item-shape")
        assert finding.message.startswith("item 2:")
        assert "just text" not in finding.message


class TestCheckReportsCrossReferenceAndLayoutWarnings:
    def test_a_body_opening_with_a_marker_for_another_rule_is_a_misnamed_body_warning(
        self, tmp_path
    ):
        root = build(
            tmp_path,
            "defaults: ['all:*']\n",
            bodies={"voice": "<!-- rule: sorting -->\ntext\n"},
        )

        result = check(root)

        assert result.returncode == 0
        (finding,) = findings(result)
        assert (finding.file, finding.line) == (str(root / "rules" / "voice.md"), 1)
        assert (finding.severity, finding.kind) == ("warning", "marker-for-another-rule")


class TestCheckWarnsWhereARuleNamesAnotherRule:
    def test_one_rules_text_holding_anothers_name_warns_naming_both_and_a_self_name_draws_none(
        self, tmp_path
    ):
        root = build(
            tmp_path,
            "defaults: ['all:*']\n",
            ["sorting"],
            {
                "report-format": "Follow sorting before you list items\n",
                "voice": "The voice rule keeps one voice\n",
            },
        )

        result = check(root)

        assert result.returncode == 0
        (finding,) = findings(result)
        assert (finding.severity, finding.kind) == ("warning", "cross-reference")
        assert finding.file == str(root / "rules" / "report-format.md")
        assert "`report-format`" in finding.message
        assert "`sorting`" in finding.message

    def test_the_warning_names_the_holder_then_the_named_rule_with_the_variant_file_and_line(
        self, tmp_path
    ):
        root = build(
            tmp_path,
            "defaults: ['all:*']\n",
            ["sorting", "voice"],
            {"voice@terse": "Be terse.\nBe brief.\nPrefer sorting here.\nsorting again\n"},
        )

        result = check(root)

        (finding,) = findings(result)
        assert finding.kind == "cross-reference"
        assert (finding.file, finding.line) == (str(root / "rules" / "voice@terse.md"), 3)
        assert finding.message.index("`voice`") < finding.message.index("`sorting`")


class TestCheckMatchesARuleNameAsAWholeWordCaseSensitive:
    def test_a_name_inside_a_longer_word_or_in_another_case_draws_no_warning(self, tmp_path):
        root = build(
            tmp_path,
            "defaults: ['all:*']\n",
            ["comments", "sorting"],
            {
                "notes": "uncomments the line\nsorting-rules\ncommentsection\nSorting\n",
                "joined": "sorting2\n_sorting\nsorting_rules\n9comments\nno-comments\n",
            },
        )

        pool = read_directory(root).pool

        assert cross_reference_warnings(pool) == ()


@pytest.fixture
def world(tmp_path):
    return World(tmp_path)


def withheld_rules(world):
    return [w["rule"] for record in world.records() for w in record["withheld"]]


class TestDeliveryWithholdsARuleCarryingACheckError:
    def test_a_rule_with_a_metadata_condition_is_withheld_while_its_ruleset_siblings_deliver(
        self, world
    ):
        world.rule("alpha")
        world.rule("beta")
        world.rule("gamma", "---\nmodel: opus\n---\ntext of gamma\n")
        world.manifest(
            DECLARED + "rulesets:\n  team: ['alpha', 'beta', 'gamma']\ndefaults: ['team:*']\n"
        )

        delivery = world.start_session()

        assert delivery.context == "text of alpha\ntext of beta\n"
        assert "gamma" in delivery.message
        assert "condition" in delivery.message
        (withheld,) = [w for r in world.records() for w in r["withheld"]]
        assert withheld["rule"] == "gamma"
        assert "condition" in withheld["error"]

    def test_a_variant_with_no_default_form_delivers_no_text_and_a_shown_notice_names_it(
        self, world
    ):
        world.rule("voice")
        world.rule("tone@dry", "dry tone text\n")
        world.manifest(DECLARED + "defaults: ['voice', 'tone@dry']\n")

        delivery = world.start_session()

        assert delivery.context == "text of voice\n"
        assert "tone" in delivery.message
        assert "default form" in delivery.message
        assert withheld_rules(world) == ["tone"]


class TestDeliverySkipsEachCycleAndBlockThatCarriesAnError:
    def test_a_block_testing_an_env_fact_does_not_apply_while_the_other_blocks_do(self, world):
        for stem in ("alpha", "beta", "gamma"):
            world.rule(stem)
        world.manifest(
            DECLARED
            + "defaults: ['alpha']\nwhen:\n  - env CI: ['beta']\n  - model opus: ['gamma']\n"
        )

        delivery = world.start_session()

        assert delivery.context == "text of alpha\ntext of gamma\n"
        assert withheld_rules(world) == []

    def test_a_spread_of_a_ruleset_in_a_cycle_reaches_no_rule_and_other_lists_apply(self, world):
        for stem in ("alpha", "beta"):
            world.rule(stem)
        world.manifest(
            DECLARED
            + "rulesets:\n  a: ['beta', 'b:*']\n  b: ['a:*']\n"
            + "defaults: ['alpha']\nwhen:\n  - model opus: ['a:*']\n"
        )

        delivery = world.start_session()

        assert delivery.context == "text of alpha\n"
        assert withheld_rules(world) == []

    def test_a_block_keyed_on_an_undeclared_flag_is_skipped_while_the_other_blocks_apply(
        self, world
    ):
        for stem in ("alpha", "beta", "gamma"):
            world.rule(stem)
        world.manifest(
            DECLARED
            + "defaults: ['alpha']\nwhen:\n"
            + "  - not flag no-such-flag: ['beta']\n  - model opus: ['gamma']\n"
        )

        delivery = world.start_session()

        assert "text of beta" not in delivery.context
        assert delivery.context == "text of alpha\ntext of gamma\n"
        assert withheld_rules(world) == []

    def test_a_block_whose_value_is_a_mapping_applies_nowhere_while_the_other_blocks_apply(
        self, world
    ):
        for stem in ("alpha", "beta", "gamma"):
            world.rule(stem)
        world.manifest(
            DECLARED
            + "defaults: ['alpha']\nwhen:\n"
            + "  - model opus: {beta: null}\n  - model opus: ['gamma']\n"
        )

        delivery = world.start_session()

        assert "text of beta" not in delivery.context
        assert delivery.context == "text of alpha\ntext of gamma\n"
        assert withheld_rules(world) == []


class TestDeliverySkipsUndeclaredReferencesReservedDeclarationsAndUnknownKeys:
    def test_an_unknown_top_level_key_is_ignored_and_the_rule_arrives_as_without_it(self, world):
        world.rule("sorting")
        world.manifest(DECLARED + "project: amboss\nwhen:\n  - model opus: ['sorting']\n")

        delivery = world.start_session()

        assert delivery.context == "text of sorting\n"
        assert delivery.message is None
        assert withheld_rules(world) == []


class TestAConflictAndAWarningWithholdNothing:
    def test_a_rule_drawing_only_a_cross_reference_warning_is_delivered(self, world):
        world.rule("report-format", "Follow sorting before you list items\n")
        world.rule("sorting")
        world.manifest(DECLARED + "defaults: ['report-format', 'sorting']\n")

        delivery = world.start_session()

        assert delivery.context == "Follow sorting before you list items\ntext of sorting\n"
        assert withheld_rules(world) == []
