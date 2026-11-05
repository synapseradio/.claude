#!/usr/bin/env python3
"""Explain traces one rule through one context, so a person sees which manifest line decided it.

Serves the rule author who asks why an agent did or did not receive a rule, and in which form.
Each case builds its rulesets directory under `tmp_path`, runs the `explain` subcommand as a
script, as a person does, and reads the lines it prints. Expected values come from the specs and
the fixture files, never from the engine's own composition.

Run with `python3.14 -m pytest features/plugins/rulesets/tests/test_composition_explain.py`.
"""

import pathlib
import re
import subprocess
import sys

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]
CLI = PLUGIN_ROOT / "lib" / "rulesets" / "cli.py"

sys.path.insert(0, str(PLUGIN_ROOT / "lib"))

from rulesets.compose.composition import compose  # noqa: E402  (path must be set before this import)
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
        assert attribute(added, "variant") == []
        assert [row[3] for row in attribute(removed, "inclusion")] == ["-sorting"]
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

    def test_a_rule_with_only_a_variant_file_is_stated_as_withheld_with_its_error(self, tmp_path):
        root = build(tmp_path, None, bodies={"tone@dry": "dry tone\n"})

        result = explain(root, "tone")

        withheld = next(line for line in result.stdout.splitlines() if line.startswith("withheld:"))
        assert "`tone` is withheld" in withheld
        assert "variant `dry` and no default form" in withheld


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

        assert result.returncode != 0
        assert "no-such-rule" in result.stderr
