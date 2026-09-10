#!/usr/bin/env python3
"""Tests for `scripts/agent-configs/render-working-rules.py`.

Run with `python3.14 -m pytest scripts/tests/test_render_working_rules.py`.

Every test builds its own tree under a tmp_path and passes a Targets naming
it, so no test reads or writes this checkout's own configuration.
"""

import dataclasses
import importlib.util
import itertools
import pathlib
import re
import subprocess
import sys

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]

sys.path.insert(0, str(REPO_ROOT / "scripts" / "agent-configs"))
import projection  # noqa: E402  (path must be set before this import)

_RENDER_PATH = REPO_ROOT / "scripts" / "agent-configs" / "render-working-rules.py"
_spec = importlib.util.spec_from_file_location("render_working_rules_test", _RENDER_PATH)
assert _spec is not None and _spec.loader is not None
render = importlib.util.module_from_spec(_spec)
sys.modules["render_working_rules_test"] = render
_spec.loader.exec_module(render)


def _write(path: pathlib.Path, text: str) -> pathlib.Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _git(repo: pathlib.Path, *args: str) -> None:
    """Run one git command in `repo`, with the user's hooks and signing off."""

    subprocess.run(
        ["git", "-C", str(repo), "-c", "core.hooksPath=", "-c", "commit.gpgsign=false", *args],
        check=True,
        capture_output=True,
    )


PREAMBLE = "## Hello from the user\n\nPlay, per [x](./rules/alpha.md)."
RENDERED_PREAMBLE = PREAMBLE.replace("./rules/alpha.md", "$HOME/.claude/rules/alpha.md")

FENCED_RULE_MARKER = "```\n<!-- rule: a-template-not-a-boundary -->\n```"


def _body(name: str, text: str) -> str:
    return f"<!-- rule: {name} -->\n\n## {name}\n\n{text}"


ALPHA = _body("alpha", "Alpha holds.")
ZETA = _body("zeta", f"Zeta holds.\n\n{FENCED_RULE_MARKER}")
EDITED = _body("alpha", "Alpha holds, as edited in the render.")


def _reference(preamble: str, *sections: str, title: str = "# Working Rules") -> str:
    """A render assembled from a preamble and whatever sections follow."""

    return "\n\n".join([title, preamble, *sections]) + "\n"


def _targets(tmp_path: pathlib.Path, *, order=("alpha", "zeta")) -> projection.Targets:
    claude_home = tmp_path / "claude"
    _write(claude_home / "CLAUDE.md", f"{PREAMBLE}\n")
    rules = claude_home / projection.RULESETS_DIRNAME / projection.DEFAULT_MODEL
    _write(rules / "alpha.md", f"{ALPHA}\n")
    _write(rules / "zeta.md", f"{ZETA}\n")
    _write(
        rules / "gated.md",
        f'---\npaths:\n  - "**/*.sh"\n---\n\n{_body("gated", "Gated holds.")}\n',
    )
    return projection.Targets(
        claude_home=claude_home,
        pi_home=tmp_path / "pi",
        opencode_home=tmp_path / "opencode",
        working_rules_order=order,
    )


def _committed(tmp_path: pathlib.Path) -> projection.Targets:
    """The same tree, plus its render, committed in a git repository."""

    targets = _targets(tmp_path)
    _write(
        targets.working_rules,
        render.build_working_rules(
            targets.claude_md, targets.rules_dir, targets.working_rules_order
        ),
    )
    _git(targets.claude_home, "init", "-q")
    _git(targets.claude_home, "config", "user.email", "test@example.invalid")
    _git(targets.claude_home, "config", "user.name", "Test")
    _git(targets.claude_home, "add", "-A")
    _git(targets.claude_home, "commit", "-q", "-m", "the tree as a run last left it")
    return targets


class TestForwardRoundTrip:
    """Task 3.2: render forward, then split in reverse over that output."""

    def test_every_source_file_survives_the_round_trip(self, tmp_path):
        targets = _targets(tmp_path)
        sources = [targets.claude_md, targets.rules_dir / "alpha.md", targets.rules_dir / "zeta.md"]
        before = {path: path.read_text(encoding="utf-8") for path in sources}

        projection.apply_plan(render.build_forward_plan(targets), check=False)
        projection.apply_plan(render.build_reverse_plan(targets), check=False)

        after = {path: path.read_text(encoding="utf-8") for path in sources}
        assert after == before, (
            "a source that does not come back byte for byte drifts a little on every sync"
        )


class TestReverseRoundTrip:
    """Task 3.3: split first over an unchanged render, then render forward
    from the sources the split wrote.

    Starting from the split, rather than from a forward render, is what puts
    the split's own output under test as a render input.
    """

    def test_the_render_survives_the_round_trip(self, tmp_path):
        targets = _targets(tmp_path)
        original = render.build_working_rules(
            targets.claude_md, targets.rules_dir, targets.working_rules_order
        )
        _write(targets.working_rules, original)

        projection.apply_plan(render.build_reverse_plan(targets), check=False)
        rebuilt = render.build_working_rules(
            targets.claude_md, targets.rules_dir, targets.working_rules_order
        )

        assert rebuilt == original, (
            "a render that does not come back byte for byte drifts a little on every sync"
        )


class TestASourceInTheWrongForm:
    """Task 3.4: a source in the wrong marker form stops the run before it writes."""

    def test_a_claude_md_carrying_a_rule_marker_stops_the_run_naming_it(self, tmp_path):
        targets = _targets(tmp_path)
        _write(
            targets.claude_md,
            "# Stance\n\n<!-- rule: stance -->\n\n## stance\n\nWork here proceeds as play.\n",
        )

        with pytest.raises(ValueError, match=re.escape(str(targets.claude_md))):
            render.build_forward_plan(targets)

        assert not targets.working_rules.exists(), (
            "a source in the wrong form must stop the run before anything is written"
        )

    def test_a_rules_file_without_one_rule_marker_stops_the_run_and_names_it(self, tmp_path):
        targets = _targets(tmp_path)
        bad = targets.rules_dir / "alpha.md"
        _write(bad, "# Alpha\n\nThis carries no rule marker.\n")

        with pytest.raises(ValueError, match=re.escape(str(bad))):
            render.build_forward_plan(targets)

        assert not targets.working_rules.exists(), (
            "a source in the wrong form must stop the run before anything is written"
        )


class TestCheckModeCarriesNoRefusal:
    """The uncommitted-changes guard belongs to the write path, not the plan.

    `--check` builds the same plan `apply_plan` reports drift from, and must
    reach it without the guard running, since a run that only reads risks
    nothing a commit could lose.
    """

    def test_forward_check_builds_the_plan_despite_an_uncommitted_render(self, tmp_path):
        targets = _committed(tmp_path)
        _write(targets.working_rules, "hand-edited, never committed\n")

        plan = render.build_forward_plan(targets, check=True)

        assert plan.files, (
            "a check that only reads must reach the plan even where a target is dirty, "
            "since it writes nothing that dirty state could put at risk"
        )

    def test_forward_write_refuses_the_same_uncommitted_render(self, tmp_path):
        targets = _committed(tmp_path)
        _write(targets.working_rules, "hand-edited, never committed\n")

        with pytest.raises(ValueError, match=re.escape("working-rules.md")):
            render.build_forward_plan(targets, check=False)

    def test_reverse_check_builds_the_plan_despite_an_uncommitted_source(self, tmp_path):
        targets = _committed(tmp_path)
        _write(targets.rules_dir / "alpha.md", f"{_body('alpha', 'Alpha, edited.')}\n")

        plan = render.build_reverse_plan(targets, check=True)

        assert plan.files, (
            "a check that only reads must reach the plan even where a source is dirty"
        )

    def test_reverse_write_refuses_the_same_uncommitted_source(self, tmp_path):
        targets = _committed(tmp_path)
        _write(targets.rules_dir / "alpha.md", f"{_body('alpha', 'Alpha, edited.')}\n")

        with pytest.raises(ValueError, match=re.escape("alpha.md")):
            render.build_reverse_plan(targets, check=False)


class TestCheckModeReportsDrift:
    """`config-projection` requirement: a check mode reports drift without writing.

    Scenarios: Everything in sync, and One output has drifted.
    """

    def test_forward_check_exits_zero_when_the_render_matches_its_sources(self, tmp_path):
        targets = _targets(tmp_path)
        render.main([], targets=targets)

        assert render.main(["--check"], targets=targets) == 0, (
            "a render this job just wrote from these sources is by definition in sync"
        )

    def test_forward_check_names_the_render_after_a_rule_body_changes(self, tmp_path, capsys):
        targets = _targets(tmp_path)
        render.main([], targets=targets)
        rendered = targets.working_rules.read_text(encoding="utf-8")
        _write(targets.rules_dir / "alpha.md", f"{_body('alpha', 'Alpha, edited.')}\n")
        capsys.readouterr()

        code = render.main(["--check"], targets=targets)
        printed = capsys.readouterr().out

        assert code != 0, "a rule body that never reached the render is drift"
        assert str(targets.working_rules) in printed, (
            "a check that reports drift without naming the path leaves the reader hunting "
            "for which of the outputs moved"
        )
        assert targets.working_rules.read_text(encoding="utf-8") == rendered, (
            "a check reports a difference without repairing it"
        )

    def test_forward_check_reports_drift_rather_than_refusing_on_a_dirty_render(
        self, tmp_path, capsys
    ):
        targets = _committed(tmp_path)
        _write(targets.working_rules, "hand-edited, never committed\n")
        capsys.readouterr()

        code = render.main(["--check"], targets=targets)
        printed = capsys.readouterr().out

        assert code != 0, "the render on disk differs from what the sources produce"
        assert str(targets.working_rules) in printed, (
            "a refusal here would report the tree as dirty in place of the drift the check "
            "exists to find, and the gate runs this against a tree carrying a staged render"
        )

    def test_reverse_check_exits_zero_when_the_sources_match_the_render(self, tmp_path):
        targets = _targets(tmp_path)
        render.main([], targets=targets)

        assert render.main(["--check", "--reverse"], targets=targets) == 0, (
            "sources a reverse run would rewrite byte for byte are by definition in sync"
        )

    def test_reverse_check_names_the_source_that_drifted(self, tmp_path, capsys):
        targets = _targets(tmp_path)
        render.main([], targets=targets)
        drifted = targets.rules_dir / "alpha.md"
        _write(drifted, f"{_body('alpha', 'Alpha, edited in its own file.')}\n")
        edited = drifted.read_text(encoding="utf-8")
        capsys.readouterr()

        code = render.main(["--check", "--reverse"], targets=targets)
        printed = capsys.readouterr().out

        assert code != 0, "a source the render no longer matches is drift in this direction"
        assert str(drifted) in printed, "the check must name the file that differs"
        assert drifted.read_text(encoding="utf-8") == edited, (
            "a check reports a difference without repairing it"
        )

    def test_reverse_check_reports_drift_rather_than_refusing_on_a_dirty_source(
        self, tmp_path, capsys
    ):
        targets = _committed(tmp_path)
        drifted = targets.rules_dir / "alpha.md"
        _write(drifted, f"{_body('alpha', 'Alpha, edited.')}\n")
        capsys.readouterr()

        code = render.main(["--check", "--reverse"], targets=targets)
        printed = capsys.readouterr().out

        assert code != 0, "the source on disk differs from what the render splits into"
        assert str(drifted) in printed, (
            "a run that writes nothing overwrites nothing, so an uncommitted source is no "
            "reason to report the tree in place of the drift"
        )


class TestMain:
    def test_check_exits_nonzero_when_the_render_is_missing(self, tmp_path):
        targets = _targets(tmp_path)

        assert render.main(["--check"], targets=targets) != 0, (
            "a render that was never written differs from what a run would produce"
        )
        assert not targets.working_rules.exists(), "--check must write nothing"

    def test_no_argument_writes_the_render(self, tmp_path):
        targets = _targets(tmp_path)

        assert render.main([], targets=targets) == 0
        assert targets.working_rules.is_file(), "the forward direction is the default"

    def test_reverse_carries_a_render_edit_into_its_rules_file(self, tmp_path):
        targets = _targets(tmp_path)
        edited = _body("alpha", "Alpha, edited in the render.")
        _write(
            targets.working_rules,
            "\n\n".join([render.TITLE, PREAMBLE, edited, ZETA]) + "\n",
        )

        render.main(["--reverse"], targets=targets)

        assert (targets.rules_dir / "alpha.md").read_text(encoding="utf-8") == f"{edited}\n", (
            "the render is the form the user edits, and the reverse is what carries those edits"
        )


class TestAGeneratedFileIsOwnedWhole:
    """`config-projection` requirement: a generated file is owned whole."""

    def test_a_hand_edit_to_the_render_is_rewritten_away(self, tmp_path):
        targets = _targets(tmp_path)
        render.main([], targets=targets)
        generated = targets.working_rules.read_text(encoding="utf-8")
        _write(targets.working_rules, generated + "\nA paragraph no source produced.\n")

        render.main([], targets=targets)

        assert targets.working_rules.read_text(encoding="utf-8") == generated, (
            "the render is rewritten in full from its sources, so text added to it directly "
            "survives no run and belongs in CLAUDE.md or a rules file"
        )


class TestBuildWorkingRules:
    def _tree(self, tmp_path: pathlib.Path) -> tuple[pathlib.Path, pathlib.Path]:
        targets = _targets(tmp_path)
        return targets.claude_md, targets.rules_dir

    def test_render_opens_on_its_title_then_the_preamble(self, tmp_path):
        claude_md, rules = self._tree(tmp_path)

        built = render.build_working_rules(claude_md, rules, ("alpha", "zeta"))

        assert built.split("\n")[0] == render.TITLE, "the render owns the one h1 and opens on it"

    def test_each_rules_file_reaches_the_render_whole(self, tmp_path):
        claude_md, rules = self._tree(tmp_path)

        built = render.build_working_rules(claude_md, rules, ("alpha", "zeta"))

        assert render.parse_reference(built).rules == (
            render.RuleSection("alpha", ALPHA),
            render.RuleSection("zeta", ZETA),
        ), "a section of the render is the rules file that produced it, marker included"

    def test_rules_follow_the_given_order(self, tmp_path):
        claude_md, rules = self._tree(tmp_path)

        built = render.build_working_rules(claude_md, rules, ("zeta", "alpha"))

        assert [section.name for section in render.parse_reference(built).rules] == [
            "zeta",
            "alpha",
        ], "the render reads as one document, so the caller orders it by topic, not by filename"

    def test_path_scoped_rule_stays_out(self, tmp_path):
        claude_md, rules = self._tree(tmp_path)

        built = render.build_working_rules(claude_md, rules, ("alpha", "zeta"))

        assert "gated" not in built, "the render carries the rules that load every session"

    def test_sections_join_on_one_blank_line_and_the_file_ends_on_one_newline(self, tmp_path):
        unlinked = "## Hello from the user\n\nNo link here to resolve."
        claude_md = _write(tmp_path / "CLAUDE.md", f"{unlinked}\n\n\n")
        rules = tmp_path / "rules"
        _write(rules / "alpha.md", f"{ALPHA}\n\n\n")
        _write(rules / "zeta.md", f"{ZETA}\n")

        built = render.build_working_rules(claude_md, rules, ("alpha", "zeta"))

        assert built == _reference(unlinked, ALPHA, ZETA), (
            "trailing blank lines in a source must not vary the joint, or the render stops "
            "being a function of the source text alone"
        )

    def test_relative_link_in_the_preamble_resolves(self, tmp_path):
        claude_md, rules = self._tree(tmp_path)

        built = render.build_working_rules(claude_md, rules, ("alpha", "zeta"))

        assert "[x]($HOME/.claude/rules/alpha.md)" in built, (
            "the render sits under references/, where a link relative to ~/.claude breaks"
        )

    def test_order_naming_no_file_reports_the_stem(self, tmp_path):
        claude_md, rules = self._tree(tmp_path)

        with pytest.raises(ValueError, match="ghost"):
            render.build_working_rules(claude_md, rules, ("alpha", "zeta", "ghost"))

    def test_unconditional_rule_missing_from_the_order_reports_the_stem(self, tmp_path):
        claude_md, rules = self._tree(tmp_path)

        with pytest.raises(ValueError, match="zeta"):
            render.build_working_rules(claude_md, rules, ("alpha",))

    def test_a_rules_file_carrying_no_rule_marker_reports_its_path(self, tmp_path):
        claude_md, rules = self._tree(tmp_path)
        _write(rules / "alpha.md", "# Alpha\n\nThis applies always.\n")

        with pytest.raises(ValueError, match=re.escape("alpha.md")):
            render.build_working_rules(claude_md, rules, ("alpha", "zeta"))

    def test_a_rule_marker_disagreeing_with_the_stem_reports_both(self, tmp_path):
        claude_md, rules = self._tree(tmp_path)
        _write(rules / "alpha.md", f"{_body('alfa', 'Alpha holds.')}\n")

        with pytest.raises(ValueError, match="alfa"):
            render.build_working_rules(claude_md, rules, ("alpha", "zeta"))

    def test_a_claude_md_carrying_a_rule_marker_reports_its_path(self, tmp_path):
        claude_md, rules = self._tree(tmp_path)
        _write(
            claude_md,
            "# Stance\n\n<!-- rule: stance -->\n\n## stance\n\nWork here proceeds as play.\n",
        )

        with pytest.raises(ValueError, match=re.escape("CLAUDE.md")):
            render.build_working_rules(claude_md, rules, ("alpha", "zeta"))

    def test_an_unclosed_fence_in_a_rules_file_stops_the_run(self, tmp_path):
        claude_md, rules = self._tree(tmp_path)
        _write(
            rules / "alpha.md",
            "<!-- rule: alpha -->\n\n## alpha\n\nA.\n\n```\nno closing fence\n",
        )

        with pytest.raises(ValueError, match=re.escape(str(rules / "alpha.md"))):
            render.build_working_rules(claude_md, rules, ("alpha", "zeta"))

    def test_a_body_carrying_a_second_rule_marker_stops_the_run_and_names_it(self, tmp_path):
        claude_md, rules = self._tree(tmp_path)
        _write(
            rules / "alpha.md",
            "<!-- rule: alpha -->\n\n## alpha\n\nA.\n\n<!-- rule: zeta -->\n\n## zeta\n\nZ.\n",
        )

        with pytest.raises(ValueError, match=re.escape(str(rules / "alpha.md"))):
            render.build_working_rules(claude_md, rules, ("alpha", "zeta"))

    def test_a_fenced_marker_is_no_second_marker(self, tmp_path):
        claude_md, rules = self._tree(tmp_path)
        _write(
            rules / "alpha.md",
            "<!-- rule: alpha -->\n\n## alpha\n\nA.\n\n```\n<!-- rule: zeta -->\n```\n",
        )

        built = render.build_working_rules(claude_md, rules, ("alpha", "zeta"))

        assert [section.name for section in render.parse_reference(built).rules] == [
            "alpha",
            "zeta",
        ], (
            "a marker inside a fence is a template a model copies, not a second marker, so "
            "a body carrying only that stays legal"
        )

    def test_the_render_survives_markdownlint_structurally(self, tmp_path):
        claude_md, rules = self._tree(tmp_path)
        built = render.build_working_rules(claude_md, rules, ("alpha", "zeta"))

        lines = built.split("\n")
        markers, _ = render._markers_outside_fences(built)
        for index, _stem in markers:
            assert lines[index - 1] == "", (
                "a marker pressed against the line above it is what markdownlint rewrites"
            )
            assert lines[index + 1] == "", (
                "a marker pressed against the ## heading below it is what markdownlint rewrites"
            )

        for first, second in itertools.pairwise(lines):
            assert not (first == "" and second == ""), (
                "a double blank line anywhere is what markdownlint rewrites"
            )


class TestParseReference:
    def test_the_preamble_runs_from_the_title_to_the_first_rule(self):
        parsed = render.parse_reference(_reference(PREAMBLE, _body("alpha", "Alpha holds.")))

        assert parsed.preamble == PREAMBLE, (
            "CLAUDE.md is what sits between the title and the first rule, and the title is not it"
        )

    def test_a_section_comes_back_as_the_body_it_was_built_from(self):
        alpha = _body("alpha", "Alpha holds.")

        parsed = render.parse_reference(_reference(PREAMBLE, alpha, _body("zeta", "Zeta holds.")))

        assert [section.name for section in parsed.rules] == ["alpha", "zeta"], (
            "a rule is named by the stem in its marker, which is the file stem"
        )
        assert parsed.rules[0].text == alpha, (
            "the section carries its marker, so the rules file it lands in is the section itself"
        )

    def test_a_rule_marker_inside_a_fence_opens_no_section(self):
        zeta = _body("zeta", FENCED_RULE_MARKER)

        parsed = render.parse_reference(_reference(PREAMBLE, _body("alpha", "A."), zeta))

        assert [section.name for section in parsed.rules] == ["alpha", "zeta"], (
            "a fenced block is a template a model copies, and a marker inside it is text"
        )
        assert parsed.rules[1].text == zeta, "the fenced marker stays inside the rule carrying it"

    def test_a_document_not_opening_on_the_title_raises(self):
        document = _reference(PREAMBLE, _body("alpha", "A."), title="# Rules")

        with pytest.raises(ValueError, match=re.escape(render.TITLE)):
            render.parse_reference(document)

    def test_a_document_with_no_preamble_raises(self):
        with pytest.raises(ValueError):
            render.parse_reference(_reference("", _body("alpha", "A.")))

    def test_a_trailing_paragraph_after_the_last_section_lands_inside_it(self):
        document = _reference(PREAMBLE, _body("alpha", "A."), "A loose sentence.")

        parsed = render.parse_reference(document)

        assert parsed.rules[-1].text.endswith("A loose sentence."), (
            "every line after a marker belongs to the section above it, so a trailing "
            "paragraph with no marker of its own comes back inside that rule's text"
        )

    def test_a_document_carrying_no_marker_parses_to_no_section(self):
        parsed = render.parse_reference(_reference(PREAMBLE))

        assert parsed.rules == () and parsed.preamble == PREAMBLE, (
            "a render with a preamble and no marker carries no section, and reporting that "
            "as an empty tuple is what lets the order check name every stem the render lost"
        )

    def test_a_marker_ends_the_section_above_it(self):
        parsed = render.parse_reference(
            _reference(PREAMBLE, _body("alpha", "A."), _body("zeta", "Z."))
        )

        assert render.marker_line("zeta") not in parsed.rules[0].text, (
            "a section runs to the next marker, not past it, so the marker that opens the "
            "next section never lands inside the one above it"
        )

    def test_a_parsed_section_carries_no_blank_line_from_the_join(self):
        parsed = render.parse_reference(
            _reference(PREAMBLE, _body("alpha", "A."), _body("zeta", "Z."))
        )

        assert not parsed.rules[0].text.endswith("\n") and not parsed.rules[1].text.startswith(
            "\n"
        ), (
            "the blank line between sections belongs to the double-newline join, which the "
            "closing </rule> used to absorb, so a parsed section neither opens nor closes on it"
        )

    def test_an_unclosed_fence_raises_in_parse_reference(self):
        document = _reference(PREAMBLE, _body("alpha", "A.") + "\n\n```\nno closing fence")

        with pytest.raises(ValueError, match=re.escape("```")):
            render.parse_reference(document)

    def test_an_indented_marker_opens_no_section(self):
        document = _reference(PREAMBLE, "  <!-- rule: zeta -->\n\n## zeta\n\nZ.")

        assert render.parse_reference(document).rules == (), (
            "matching is fullmatch against a whole line, so a marker indented off column 0 "
            "opens no section, and a document whose only candidate is indented carries none"
        )

    def test_a_marker_with_trailing_text_opens_no_section(self):
        document = _reference(PREAMBLE, "<!-- rule: zeta --> extra\n\n## zeta\n\nZ.")

        assert render.parse_reference(document).rules == (), (
            "matching is fullmatch against a whole line, so trailing text after the marker "
            "opens no section, and a document whose only candidate carries it has none"
        )


class TestBuildReversePlan:
    def _files(self, targets, *sections, order=None) -> dict:
        aimed = (
            targets if order is None else dataclasses.replace(targets, working_rules_order=order)
        )
        _write(aimed.working_rules, _reference(RENDERED_PREAMBLE, *sections))
        return {f.path: f.content for f in render.build_reverse_plan(aimed).files}

    def test_each_rule_body_lands_in_its_own_rules_file(self, tmp_path):
        files = self._files(_targets(tmp_path), ALPHA, ZETA)

        assert files[_targets(tmp_path).rules_dir / "alpha.md"] == f"{ALPHA}\n", (
            "a rules file is the render's section for it, marker included and nothing above it"
        )

    def test_the_preamble_lands_in_claude_md_with_its_paths_restored(self, tmp_path):
        targets = _targets(tmp_path)
        files = self._files(targets, ALPHA, ZETA)

        assert files[targets.claude_md] == f"{PREAMBLE}\n", (
            "CLAUDE.md sits inside ~/.claude, where the render's resolved link does not belong"
        )

    def test_the_reverse_touches_the_sources_and_nothing_else(self, tmp_path):
        targets = _targets(tmp_path)
        _write(targets.working_rules, _reference(RENDERED_PREAMBLE, ALPHA, ZETA))

        plan = render.build_reverse_plan(targets)

        assert {f.path for f in plan.files} == {
            targets.claude_md,
            targets.rules_dir / "alpha.md",
            targets.rules_dir / "zeta.md",
        }, "the reverse writes the sources, and a forward run projects them onto pi and opencode"
        assert plan.keys == () and plan.dropped == (), (
            "no generated key and no agent translation belongs to this direction"
        )

    def test_a_rule_body_whose_file_does_not_exist_yet_gets_one(self, tmp_path):
        targets = _targets(tmp_path)
        (targets.rules_dir / "zeta.md").unlink()

        files = self._files(targets, ALPHA, ZETA)

        assert files[targets.rules_dir / "zeta.md"] == f"{ZETA}\n", (
            "a rule added to the render creates its file, with its stem added to the order"
        )

    def test_a_rule_the_order_does_not_name_raises(self, tmp_path):
        with pytest.raises(ValueError, match="ghost"):
            self._files(_targets(tmp_path), ALPHA, ZETA, _body("ghost", "Ghost holds."))

    def test_rules_out_of_the_order_sequence_raise(self, tmp_path):
        with pytest.raises(ValueError, match="zeta"):
            self._files(_targets(tmp_path), ZETA, ALPHA)

    def test_a_rule_resolving_to_a_path_scoped_file_raises(self, tmp_path):
        with pytest.raises(ValueError, match=re.escape("gated.md")):
            self._files(
                _targets(tmp_path),
                ALPHA,
                _body("gated", "G."),
                order=("alpha", "gated"),
            )


class TestBuildForwardPlan:
    def test_the_render_lands_under_references(self, tmp_path):
        targets = _targets(tmp_path)

        plan = render.build_forward_plan(targets)
        by_path = {f.path: f.content for f in plan.files}
        written = by_path[targets.claude_home / "references" / "default" / "working-rules.md"]

        assert ALPHA in written and "gated" not in written, (
            "the render carries the preamble and every always-on rule, and no path-scoped one"
        )


class TestRefusesToOverwriteUncommittedWork:
    """`config-projection` requirement: a job refuses to overwrite uncommitted work."""

    def test_the_forward_direction_runs_against_a_clean_tree(self, tmp_path):
        targets = _committed(tmp_path)

        plan = render.build_forward_plan(targets)

        assert targets.working_rules in {generated.path for generated in plan.files}, (
            "a tree whose every change is committed has nothing a run could destroy"
        )

    def test_the_forward_direction_runs_with_a_source_carrying_uncommitted_work(self, tmp_path):
        targets = _committed(tmp_path)
        _write(targets.rules_dir / "alpha.md", f"{EDITED}\n")

        built = render.build_working_rules(
            targets.claude_md, targets.rules_dir, targets.working_rules_order
        )

        assert EDITED in built and render.build_forward_plan(targets).files, (
            "the source side is what this direction reads, and reading destroys nothing"
        )

    def test_the_reverse_direction_runs_against_a_clean_tree(self, tmp_path):
        targets = _committed(tmp_path)

        plan = render.build_reverse_plan(targets)

        assert {generated.path for generated in plan.files} == {
            targets.claude_md,
            targets.rules_dir / "alpha.md",
            targets.rules_dir / "zeta.md",
        }, "a tree whose every change is committed has nothing a run could destroy"

    def test_the_reverse_direction_refuses_a_claude_md_carrying_uncommitted_work(self, tmp_path):
        targets = _committed(tmp_path)
        _write(
            targets.claude_md, f"{PREAMBLE}\n\n<what_wins>\n\nNearness decides.\n\n</what_wins>\n"
        )

        with pytest.raises(ValueError, match=re.escape("CLAUDE.md")):
            render.build_reverse_plan(targets)

    def test_the_reverse_direction_runs_with_a_render_carrying_uncommitted_work(self, tmp_path):
        targets = _committed(tmp_path)
        _write(targets.working_rules, _reference(RENDERED_PREAMBLE, EDITED, ZETA))

        files = {
            generated.path: generated.content
            for generated in render.build_reverse_plan(targets).files
        }

        assert files[targets.rules_dir / "alpha.md"] == f"{EDITED}\n", (
            "an uncommitted render edit is the whole reason to run this direction"
        )

    def test_a_dirty_target_reports_every_file_it_would_have_overwritten(self, tmp_path):
        targets = _committed(tmp_path)
        _write(
            targets.claude_md, f"{PREAMBLE}\n\n<what_wins>\n\nNearness decides.\n\n</what_wins>\n"
        )
        _write(targets.rules_dir / "alpha.md", f"{EDITED}\n")

        with pytest.raises(ValueError) as raised:
            render.build_reverse_plan(targets)

        assert "CLAUDE.md" in str(raised.value) and "alpha.md" in str(raised.value), (
            "a refusal naming one of two dirty files sends the reader back for the second"
        )

    def test_a_tree_outside_a_git_repository_runs(self, tmp_path):
        assert render.build_forward_plan(_targets(tmp_path)).files, (
            "a checkout is not required, so configuration nobody versions still syncs"
        )


class TestDirection:
    def test_reverse_leaves_the_render_as_it_found_it(self, tmp_path):
        targets = _targets(tmp_path)
        rendered = _reference(RENDERED_PREAMBLE, EDITED, ZETA)
        _write(targets.working_rules, rendered)

        render.main(["--reverse"], targets=targets)

        assert targets.working_rules.read_text(encoding="utf-8") == rendered, (
            "one run moves text one way, so the side it read from stands untouched"
        )

    def test_check_with_reverse_reports_a_pending_edit_and_writes_nothing(self, tmp_path):
        targets = _targets(tmp_path)
        _write(targets.working_rules, _reference(RENDERED_PREAMBLE, EDITED, ZETA))
        untouched = (targets.rules_dir / "alpha.md").read_text(encoding="utf-8")

        assert render.main(["--check", "--reverse"], targets=targets) != 0, (
            "a render edit that never reached its rules file is what this reports"
        )
        assert (targets.rules_dir / "alpha.md").read_text(encoding="utf-8") == untouched, (
            "--check reports a difference without repairing it, whichever direction it runs"
        )


class TestRoundTrip:
    def test_a_render_survives_a_reverse_then_a_forward_run(self, tmp_path):
        targets = _targets(tmp_path)
        rendered = _reference(RENDERED_PREAMBLE, EDITED, ZETA)
        _write(targets.working_rules, rendered)

        render.main(["--reverse"], targets=targets)
        rebuilt = render.build_working_rules(
            targets.claude_md, targets.rules_dir, targets.working_rules_order
        )

        assert rebuilt == rendered, (
            "a render that does not come back byte for byte drifts a little on every sync"
        )

    def test_the_repository_render_survives_the_round_trip(self, tmp_path):
        default = projection.DEFAULT_TARGETS
        original = default.working_rules.read_text(encoding="utf-8")
        claude_home = tmp_path / "claude"
        _write(claude_home / default.working_rules.relative_to(default.claude_home), original)
        targets = projection.Targets(
            claude_home=claude_home,
            pi_home=tmp_path / "pi",
            opencode_home=tmp_path / "opencode",
        )

        render.main(["--reverse"], targets=targets)
        rebuilt = render.build_working_rules(
            targets.claude_md, targets.rules_dir, targets.working_rules_order
        )

        assert rebuilt == original, (
            "the render this repository carries is the corpus the two directions run against, "
            "and a fixture that round trips proves nothing about it"
        )


class TestOneReferenceFilePerModel:
    """Each model's own bodies, rendered under that model's own name."""

    def _tree(self, tmp_path: pathlib.Path) -> projection.Targets:
        """A checkout whose `haiku` model overrides one of default's two bodies."""

        targets = _targets(tmp_path)
        _write(
            targets.claude_home / projection.RULESETS_DIRNAME / "haiku" / "alpha.md",
            f"{_body('alpha', 'Alpha holds, for haiku.')}\n",
        )
        return targets

    def test_every_model_directory_gets_a_render_under_its_own_name(self, tmp_path):
        targets = self._tree(tmp_path)

        written = {generated.path for generated in render.build_forward_plan(targets).files}

        assert written == {
            targets.claude_home / "references" / "default" / "working-rules.md",
            targets.claude_home / "references" / "haiku" / "working-rules.md",
        }, (
            "a model reads its own rules, so the reference showing what it reads belongs under "
            "its own name, and one shared render can only show one model's"
        )

    def test_a_model_render_carries_that_model_s_own_bodies_alone(self, tmp_path):
        targets = self._tree(tmp_path)

        rendered = {
            generated.path.parent.name: generated.content
            for generated in render.build_forward_plan(targets).files
        }

        assert "Alpha holds, for haiku." in rendered["haiku"], (
            "the render for a model reads that model's own directory, so its override is what "
            "lands there"
        )
        assert "Zeta holds." not in rendered["haiku"], (
            "haiku's directory holds no zeta, and pulling default's in would make the reference "
            "claim an override the model never carries"
        )
        assert "Alpha holds." in rendered["default"] and "Zeta holds." in rendered["default"], (
            "default's render still carries every body its own directory holds"
        )

    def test_a_body_the_order_does_not_name_stops_the_run(self, tmp_path):
        targets = self._tree(tmp_path)
        _write(
            targets.claude_home / projection.RULESETS_DIRNAME / "haiku" / "unlisted.md",
            f"{_body('unlisted', 'Unlisted holds.')}\n",
        )

        with pytest.raises(ValueError, match="unlisted"):
            render.build_forward_plan(targets)

    def test_the_check_mode_reports_one_model_render_drifting(self, tmp_path, capsys):
        targets = self._tree(tmp_path)
        for generated in render.build_forward_plan(targets, check=True).files:
            _write(generated.path, generated.content)
        drifting = targets.claude_home / "references" / "haiku" / "working-rules.md"
        _write(drifting, drifting.read_text(encoding="utf-8") + "\nhand-added\n")

        code = render.main(["--check"], targets=targets)

        assert code != 0, "a reference file that stopped matching its model's bodies has to report"
        assert str(drifting) in capsys.readouterr().out, (
            "the report names the file to regenerate, so a reader fixes the one that drifted"
        )
