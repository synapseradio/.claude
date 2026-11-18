#!/usr/bin/env python3
"""Explain and check tell a rule author what the engine will deliver and what it will not.

Serves the rule author who asks why an agent did or did not receive a rule, and who runs check
before trusting a delivery. Each case builds its rulesets directory under `tmp_path`, runs the
`explain` or `check` subcommand as a script, or a hook delivery, as a person and the harness do,
and reads what they print or receive. Expected values come from `docs/commands.md` and the
fixture files, never from the engine's own composition.

Run with `python3.15 -m pytest features/plugins/rulesets/tests/test_composition_explain.py`.
"""

import pathlib
import re
import subprocess
import sys
from typing import NamedTuple

import pytest
from delivery_world import DECLARED

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]
CLI = PLUGIN_ROOT / "lib" / "rulesets" / "cli.py"


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


def cli(*arguments) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(CLI), *arguments],
        capture_output=True,
        text=True,
        check=False,
        cwd=CLI.parent,
    )


def explain(root, rule, *options) -> subprocess.CompletedProcess[str]:
    return cli("explain", rule, "--root", str(root), *options)


def check(root) -> subprocess.CompletedProcess[str]:
    return cli("check", "--root", str(root))


class Finding(NamedTuple):
    file: str
    line: int | None
    severity: str
    kind: str
    message: str


_FINDING = re.compile(
    r"(?P<file>.+?)(?::(?P<line>\d+))?: (?P<severity>error|warning) \[(?P<kind>[^\]]+)\] (?P<message>.*)"
)


def findings(result) -> list[Finding]:
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


def attribute(result, name) -> list[list[str]]:
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


def header(result, name) -> str | None:
    """The line that opens the attribute `name`, or None where the output has none."""
    return next(
        (line for line in result.stdout.splitlines() if line.startswith(f"{name}:")),
        None,
    )


def leading_cells(rows, expected) -> list[list[str]]:
    """Each row cut to the cells its expected row names, for comparing the cells a case states."""
    return [row[: len(want)] for row, want in zip(rows, expected, strict=False)]


class TestExplainTracesOneRuleInOneContext:
    @pytest.mark.parametrize(
        ("config", "stems", "rule", "options", "conditions"),
        [
            (
                "models: haiku\n"
                "flags: strict\n"
                "not flag strict:\n"
                "  include: voice\n"
                "not agent eval-runner:\n"
                "  exclude: voice\n",
                ["voice"],
                "voice",
                ["--model", "haiku"],
                ["not flag strict"],
            ),
            (
                "defaults: voice\nnot kind delegate:\n  exclude: voice\n",
                ["voice"],
                "voice",
                [],
                ["defaults"],
            ),
            (
                "defaults: voice\nnot kind delegate:\n  exclude: voice\n",
                ["voice"],
                "voice",
                ["--kind", "session"],
                ["not kind delegate", "defaults"],
            ),
            (
                "models: opus haiku\ndefaults: writing-code\nmodel haiku:\n  exclude: writing-code\n",
                ["writing-code"],
                "writing-code",
                ["--model", "opus"],
                ["defaults"],
            ),
        ],
        ids=[
            "a fact left out is absent and a flag left out is unset",
            "a kind left unnamed is unknown so a block testing its negation does not apply",
            "a kind named session makes that block apply",
            "a block testing another model is absent from the output",
        ],
    )
    def test_the_lines_listed_are_those_whose_conditions_hold_in_the_named_context(
        self, tmp_path, config, stems, rule, options, conditions
    ) -> None:
        root = build(tmp_path, config, stems)

        result = explain(root, rule, *options)

        assert result.returncode == 0
        assert [row[2] for row in attribute(result, "inclusion")] == conditions


class TestExplainPrintsInclusionAndVariantEachOpeningWithTheWinner:
    def test_each_attribute_opens_with_its_winner_and_lists_the_lines_it_beat(
        self, tmp_path
    ) -> None:
        root = build(
            tmp_path,
            "models: haiku\n"
            "defaults: writing-prose\n"
            "model haiku:\n"
            "  include: writing-prose@haiku\n"
            "agent eval-runner:\n"
            "  exclude: writing-prose\n",
            ["writing-prose", "writing-prose@haiku"],
        )
        config = f"{root}/config.yaml"

        result = explain(root, "writing-prose", "--model", "haiku", "--agent", "eval-runner")

        assert result.returncode == 0
        assert attribute(result, "inclusion") == [
            ["wins", f"{config}:6", "agent eval-runner", "exclude writing-prose", "names the rule"],
            ["beat", f"{config}:2", "defaults", "include writing-prose", "names the rule"],
            [
                "beat",
                f"{config}:4",
                "model haiku",
                "include writing-prose@haiku",
                "names the rule",
            ],
        ]
        assert header(result, "inclusion") == "inclusion: off"
        assert header(result, "variant") == "variant: haiku"
        assert attribute(result, "variant") == [
            ["wins", f"{config}:4", "model haiku", "include writing-prose@haiku", "names the rule"],
        ]


class TestExplainQuotesEachLineAsTheConfigWritesIt:
    @pytest.mark.parametrize(
        ("config", "stems", "rule", "options", "expected"),
        [
            (
                "sets:\n  bash: shell-scripts\n"
                + "".join(f"# line {n}\n" for n in range(3, 39))
                + "kind session:\n  exclude: bash.shell-scripts\ndefaults: all.*\n",
                ["shell-scripts"],
                "shell-scripts",
                ["--kind", "session"],
                [["wins", "{config}:40", "kind session", "exclude bash.shell-scripts"]],
            ),
            (
                "models: opus haiku\n"
                "sets:\n"
                "  planning: writing-plans\n"
                "agent Plan:\n"
                "  not model haiku:\n"
                "    include: planning.*\n",
                ["writing-plans"],
                "writing-plans",
                ["--agent", "Plan", "--model", "opus"],
                [
                    [
                        "wins",
                        "{config}:6",
                        "agent Plan and not model haiku",
                        "include planning.*",
                        "through ruleset planning",
                    ]
                ],
            ),
            (
                "models: haiku\nsets:\n  reviewer: report-format\nmodel haiku:\n"
                "  include: reviewer.*\n",
                ["report-format"],
                "report-format",
                ["--model", "haiku"],
                [
                    [
                        "wins",
                        "{config}:5",
                        "model haiku",
                        "include reviewer.*",
                        "through ruleset reviewer",
                    ]
                ],
            ),
            (
                "defaults: outer.*\nsets:\n  outer: inner.*\n  inner: voice\n",
                ["voice"],
                "voice",
                [],
                [
                    [
                        "wins",
                        "{config}:1",
                        "defaults",
                        "include outer.*",
                        "through ruleset outer > inner",
                    ]
                ],
            ),
            (
                "defaults: top.*\n"
                "sets:\n"
                "  top: middle.* sorting\n"
                "  middle: bottom.*\n"
                "  bottom: voice\n",
                ["voice", "sorting"],
                "voice",
                [],
                [
                    [
                        "wins",
                        "{config}:1",
                        "defaults",
                        "include top.*",
                        "through ruleset top > middle > bottom",
                    ]
                ],
            ),
        ],
        ids=[
            "an exclude reads with its key, its set, and its line",
            "a nested block reads with its combined condition at its own line",
            "a line reaching the rule through a ruleset names the ruleset",
            "nested rulesets name the chain down to the holder",
            "a chain of three rulesets names each from the spread one down",
        ],
    )
    def test_the_winning_line_gives_its_file_line_condition_reference_and_reach(
        self, tmp_path, config, stems, rule, options, expected
    ) -> None:
        root = build(tmp_path, config, stems)
        want = [[cell.format(config=f"{root}/config.yaml") for cell in row] for row in expected]

        result = explain(root, rule, *options)

        assert leading_cells(attribute(result, "inclusion"), want) == want


class TestExplainPlacesEachLineUnderInclusionVariantOrBoth:
    @pytest.mark.parametrize(
        ("config", "rule", "options", "inclusion", "variant"),
        [
            (
                "flags: a b\nflag a:\n  include: voice\nflag b:\n  exclude: sorting\n",
                "voice",
                ["--flag", "a", "--flag", "b"],
                ["include voice"],
                [],
            ),
            (
                "flags: a b\nflag a:\n  include: voice\nflag b:\n  exclude: sorting\n",
                "sorting",
                ["--flag", "a", "--flag", "b"],
                ["exclude sorting"],
                [],
            ),
            (
                "flags: a\nflag a:\n  include: voice@terse\n",
                "voice",
                ["--flag", "a"],
                ["include voice@terse"],
                ["include voice@terse"],
            ),
            (
                "flags: a\nflag a:\n  exclude: voice@terse\n",
                "voice",
                ["--flag", "a"],
                [],
                ["exclude voice@terse"],
            ),
        ],
        ids=["a bare add", "a bare remove", "an add at a variant", "a strike"],
    )
    def test_each_line_appears_under_the_attributes_it_decides(
        self, tmp_path, config, rule, options, inclusion, variant
    ) -> None:
        root = build(tmp_path, config, ["voice", "voice@terse", "sorting"])

        result = explain(root, rule, *options)

        assert [row[3] for row in attribute(result, "inclusion")] == inclusion
        assert [row[3] for row in attribute(result, "variant")] == variant
        assert header(result, "inclusion") is not None
        assert header(result, "variant") is not None


class TestExplainStatesWhatNoLineSays:
    def test_a_flag_keyed_variant_leads_with_the_flag_and_the_default_form_is_stated_without_it(
        self, tmp_path
    ) -> None:
        root = build(
            tmp_path,
            "flags: voice-terse\ndefaults: voice\nflag voice-terse:\n  include: voice@terse\n",
            ["voice", "voice@terse"],
        )

        flagged = explain(root, "voice", "--flag", "voice-terse")
        unflagged = explain(root, "voice")

        assert header(flagged, "variant") == "variant: terse"
        assert attribute(flagged, "variant")[0][:3] == [
            "wins",
            f"{root}/config.yaml:4",
            "flag voice-terse",
        ]
        assert "the default form is delivered" in header(unflagged, "variant")
        assert attribute(unflagged, "variant") == []

    def test_a_rule_that_is_excluded_or_unreached_is_not_said_to_deliver_its_default_form(
        self, tmp_path
    ) -> None:
        root = build(
            tmp_path,
            "defaults:\n  include: voice\n  exclude: voice\n",
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

    @pytest.mark.parametrize(
        ("config", "bodies", "rule"),
        [
            ("defaults: big\n", {"big": "x" * 9001}, "big"),
            (None, {"tone@dry": "dry tone\n"}, "tone"),
        ],
        ids=["an included rule whose body is too long", "a rule with only a variant file"],
    )
    def test_a_withheld_rule_is_stated_as_withheld_and_not_said_to_deliver_its_default_form(
        self, tmp_path, config, bodies, rule
    ) -> None:
        root = build(tmp_path, config, bodies=bodies)

        result = explain(root, rule)

        withheld = [line for line in result.stdout.splitlines() if line.startswith("withheld:")]
        assert len(withheld) == 1
        assert f"`{rule}`" in withheld[0]
        assert "default form is delivered" not in result.stdout


class TestExplainLabelsEachVariantLineByWhatItDid:
    @pytest.mark.parametrize(
        ("exclude", "stems", "variant", "rows"),
        [
            (
                "voice@terse",
                ["voice", "voice@dry", "voice@terse"],
                "dry",
                [
                    ["wins", "{config}:3", "defaults", "include voice@dry", "names the rule"],
                    ["struck", "{config}:5", "model opus", "include voice@terse", "names the rule"],
                    ["strikes", "{config}:7", "flag f", "exclude voice@terse", "names the rule"],
                ],
            ),
            (
                "voice@plain",
                ["voice", "voice@dry", "voice@terse", "voice@plain"],
                "terse",
                [
                    ["wins", "{config}:5", "model opus", "include voice@terse", "names the rule"],
                    ["beat", "{config}:3", "defaults", "include voice@dry", "names the rule"],
                    ["strikes", "{config}:7", "flag f", "exclude voice@plain", "names the rule"],
                ],
            ),
        ],
        ids=[
            "a strike above the winner strikes and the add it removed is struck not beaten",
            "an add the winner outranked is beaten and a strike of another variant strikes",
        ],
    )
    def test_each_variant_line_reads_as_the_winner_a_beaten_add_a_struck_add_or_a_strike(
        self, tmp_path, exclude, stems, variant, rows
    ) -> None:
        root = build(
            tmp_path,
            "models: opus\n"
            "flags: f\n"
            "defaults: voice@dry\n"
            "model opus:\n"
            "  include: voice@terse\n"
            "flag f:\n"
            f"  exclude: {exclude}\n",
            stems,
        )

        result = explain(root, "voice", "--model", "opus", "--flag", "f")

        assert header(result, "variant") == f"variant: {variant}"
        assert attribute(result, "variant") == [
            [cell.format(config=f"{root}/config.yaml") for cell in row] for row in rows
        ]


class TestExplainNamesAConflictAndTheVariantDeliveryTakes:
    def test_both_conflicting_lines_are_listed_with_the_variant_delivery_takes(
        self, tmp_path
    ) -> None:
        config = (
            "flags: a b\n"
            "defaults: voice@plain\n"
            "flag a:\n"
            "  include: voice@terse\n"
            "flag b:\n"
            "  include: voice@dry\n"
        )
        root = build(tmp_path, config, ["voice", "voice@plain", "voice@terse", "voice@dry"])

        result = explain(root, "voice", "--flag", "a", "--flag", "b")

        file = f"{root}/config.yaml"
        rows = attribute(result, "variant")
        assert [row[:3] for row in rows[:3]] == [
            ["wins", f"{file}:2", "defaults"],
            ["conflict", f"{file}:4", "flag a"],
            ["conflict", f"{file}:6", "flag b"],
        ]
        assert rows[3] == [
            "conflict: `voice@terse` and `voice@dry` set different variants at one position; "
            "delivery takes plain"
        ]
        rendered = root / "context.md"
        render = cli(
            "render", "--flag", "a", "--flag", "b", "--out", str(rendered), "--root", str(root)
        )
        assert render.returncode == 0, render.stderr
        assert "<!-- rule: voice variant: plain -->" in rendered.read_text(encoding="utf-8")


class TestExplainExitsNonZeroOnAnUnknownRule:
    def test_a_name_the_pool_does_not_hold_fails_and_is_named(self, tmp_path) -> None:
        root = build(tmp_path, "defaults: voice\n", ["voice"])

        result = explain(root, "no-such-rule")

        assert result.returncode == 1
        assert "no-such-rule" in result.stderr
        assert "Traceback" not in result.stderr


class TestCheckReportsEveryErrorAndWarningInOneRun:
    def test_a_cycle_a_bad_condition_and_a_missing_rule_are_all_reported_with_file_and_line(
        self, tmp_path
    ) -> None:
        root = build(
            tmp_path,
            "defaults: ghost\nsets:\n  a: b.*\n  b: a.*\nproject amboss:\n  include: voice\n",
            ["voice"],
        )
        config = str(root / "config.yaml")

        result = check(root)

        assert result.returncode != 0
        found = findings(result)
        assert sorted((f.file, f.line, f.severity, f.kind) for f in found) == [
            (config, 1, "error", "undeclared-reference"),
            (config, 3, "error", "ruleset-cycle"),
            (config, 5, "error", "condition-invalid"),
        ]
        by_line = {f.line: f.message for f in found}
        assert "ghost" in by_line[1]
        assert "project" in by_line[5]

    def test_warnings_alone_are_reported_with_file_and_line_and_the_exit_status_is_zero(
        self, tmp_path
    ) -> None:
        root = build(
            tmp_path,
            "defaults: report-format\n",
            ["sorting"],
            {"report-format": "Follow `sorting` before you list items\n"},
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

    def test_a_directory_with_no_error_and_no_warning_prints_nothing_and_exits_zero(
        self, tmp_path
    ) -> None:
        root = build(tmp_path, "defaults: all.*\n", ["voice", "sorting"])

        result = check(root)

        assert (result.returncode, result.stdout, result.stderr) == (0, "", "")


class TestCheckWarnsOfARuleNoAddIncludes:
    @pytest.mark.parametrize(
        ("config", "stems", "warned"),
        [
            ("flags: never-set\nflag never-set:\n  include: voice\n", ["voice"], None),
            ("defaults: sorting\nsets:\n  team: voice\n", ["voice", "sorting"], None),
            (
                "defaults:\n  include: voice\n  exclude: sorting\n",
                ["voice", "sorting"],
                "sorting",
            ),
        ],
        ids=[
            "a rule included only by a block keyed on a flag never set",
            "a rule only a ruleset nothing spreads lists",
            "a rule that defaults removes and no list adds",
        ],
    )
    def test_only_a_rule_no_list_adds_draws_a_warning_naming_its_file(
        self, tmp_path, config, stems, warned
    ) -> None:
        root = build(tmp_path, config, stems)

        result = check(root)

        assert result.returncode == 0
        found = findings(result)
        if warned is None:
            assert found == []
        else:
            (finding,) = found
            assert (finding.severity, finding.kind) == ("warning", "never-included")
            assert finding.file == str(root / "rules" / f"{warned}.md")
            assert f"`{warned}`" in finding.message


class TestCheckReportsAnErrorForEachIllegalBlock:
    @pytest.mark.parametrize(
        ("config", "line", "fragment"),
        [
            ("defaults: voice\nproject: amboss\n", 2, "`project`"),
            (
                "models: opus\nflags: f\nflag f:\n  include: voice\nmodel opus: voice\n",
                5,
                "block `model opus`",
            ),
            (
                "sets:\n  reasoning: voice\n  lookup: tone\nagent critic: reasoning.* lookup.*\n",
                4,
                "block `agent critic`",
            ),
        ],
        ids=[
            "an unknown top-level key",
            "a block whose value is one word",
            "a block whose value is words that belong under include",
        ],
    )
    def test_the_block_is_an_error_naming_it_at_its_line(
        self, tmp_path, config, line, fragment
    ) -> None:
        root = build(tmp_path, config, ["voice", "tone"])

        result = check(root)

        assert result.returncode != 0
        (finding,) = [f for f in findings(result) if f.severity == "error"]
        assert (finding.file, finding.line) == (str(root / "config.yaml"), line)
        assert finding.kind == "block-shape"
        assert fragment in finding.message


class TestCheckReportsCrossReferenceAndLayoutWarnings:
    def test_a_body_opening_with_a_marker_for_another_rule_is_a_misnamed_body_warning(
        self, tmp_path
    ) -> None:
        root = build(
            tmp_path,
            "defaults: all.*\n",
            bodies={"voice": "<!-- rule: sorting -->\ntext\n"},
        )

        result = check(root)

        assert result.returncode == 0
        (finding,) = findings(result)
        assert (finding.file, finding.line) == (str(root / "rules" / "voice.md"), 1)
        assert (finding.severity, finding.kind) == ("warning", "marker-for-another-rule")

    @pytest.mark.parametrize(
        ("stems", "bodies", "expected"),
        [
            (
                ["sorting"],
                {
                    "report-format": "Follow `sorting` before you list items\n",
                    "voice": "The voice rule keeps one voice\n",
                },
                [("report-format.md", 1, "report-format", "sorting")],
            ),
            (
                ["sorting", "voice"],
                {"voice@terse": "Be terse.\nBe brief.\nPrefer `sorting` here.\n`sorting` again\n"},
                [("voice@terse.md", 3, "voice", "sorting")],
            ),
            (
                ["comments", "sorting"],
                {
                    "notes": "rule uncomments\nsorting-rules.md\nrule commentsection\n`Sorting`\n",
                    "joined": "sorting2.md\n_sorting.md\nrule sorting_rules\nrule 9comments\n"
                    "the no-comments rule\n",
                },
                [],
            ),
        ],
        ids=[
            "a rule naming another warns and a rule naming itself does not",
            "the warning names the holder then the named rule at the first line of a variant file",
            "a name inside a longer word or in another case draws no warning",
        ],
    )
    def test_a_rules_text_naming_another_rule_warns_naming_both(
        self, tmp_path, stems, bodies, expected
    ) -> None:
        root = build(tmp_path, "defaults: all.*\n", stems, bodies)

        result = check(root)

        assert result.returncode == 0
        found = findings(result)
        assert [(pathlib.Path(f.file).name, f.line, f.kind) for f in found] == [
            (name, line, "cross-reference") for name, line, _, _ in expected
        ]
        for finding, (_, _, holder, named) in zip(found, expected, strict=True):
            assert finding.severity == "warning"
            assert finding.message.index(f"`{holder}`") < finding.message.index(f"`{named}`")


class TestDeliverySkipsEachBlockAndCycleThatCarriesAnError:
    @pytest.mark.parametrize(
        ("config", "context"),
        [
            (
                "defaults: alpha\nenv CI:\n  include: beta\nmodel opus:\n  include: gamma\n",
                "alpha gamma",
            ),
            (
                "sets:\n  a: beta b.*\n  b: a.*\ndefaults: alpha\nmodel opus:\n  include: a.*\n",
                "alpha",
            ),
            (
                "defaults: alpha\nnot flag no-such-flag:\n  include: beta\nmodel opus:\n  include: gamma\n",
                "alpha gamma",
            ),
            (
                "defaults: alpha\nmodel opus: beta\nkind session:\n  include: gamma\n",
                "alpha gamma",
            ),
            ("project: amboss\nmodel opus:\n  include: gamma\n", "gamma"),
        ],
        ids=[
            "a block testing an env fact",
            "a spread of a ruleset in a cycle",
            "a block keyed on an undeclared flag",
            "a block whose words sit outside include",
            "an unknown top-level key",
        ],
    )
    def test_the_block_applies_nowhere_while_the_other_blocks_apply(
        self, world, config, context
    ) -> None:
        for stem in ("alpha", "beta", "gamma"):
            world.rule(stem)
        world.write_config(DECLARED + config)

        delivery = world.start_session()

        assert delivery.context == "".join(f"text of {stem}\n" for stem in context.split())
        assert world.withheld_rules() == []


class TestAWarningWithholdsNothing:
    def test_a_rule_drawing_only_a_cross_reference_warning_is_delivered(self, world) -> None:
        world.rule("report-format", "Follow sorting before you list items\n")
        world.rule("sorting")
        world.write_config(DECLARED + "defaults: report-format sorting\n")

        delivery = world.start_session()

        assert delivery.context == "Follow sorting before you list items\ntext of sorting\n"
        assert world.withheld_rules() == []
