#!/usr/bin/env python3
"""Tests for `scripts/agent-configs/render-working-rules.py`.

Run with `python3.14 -m pytest scripts/tests/test_render_working_rules.py`.

Every test builds its own tree under a tmp_path and passes a Targets naming
it, so no test reads or writes this checkout's own configuration.
"""

import importlib.util
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


PREAMBLE = '<hello from="user">\n~\n/~\n</hello>\n\n<stance>\n\nPlay.\n\n</stance>'


def _element(name: str, body: str) -> str:
    return f'<rule name="{name}">\n\n{body}\n\n</rule>'


ALPHA = _element("alpha", "Alpha holds.")
ZETA = _element("zeta", "Zeta holds.")


def _targets(tmp_path: pathlib.Path, *, order=("alpha", "zeta")) -> projection.Targets:
    claude_home = tmp_path / "claude"
    _write(claude_home / "CLAUDE.md", f"{PREAMBLE}\n")
    _write(claude_home / "rules" / "alpha.md", f"{ALPHA}\n")
    _write(claude_home / "rules" / "zeta.md", f"{ZETA}\n")
    return projection.Targets(
        claude_home=claude_home,
        pi_home=tmp_path / "pi",
        opencode_home=tmp_path / "opencode",
        working_rules_order=order,
    )


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
    """Task 3.4: a source in neither tag form stops the run before it writes."""

    def test_a_claude_md_without_the_preamble_opening_stops_the_run(self, tmp_path):
        targets = _targets(tmp_path)
        _write(targets.claude_md, "# Stance\n\nNo hello tag here.\n")

        with pytest.raises(ValueError, match=re.escape(str(targets.claude_md))):
            render.build_forward_plan(targets)

        assert not targets.working_rules.exists(), (
            "a source in the wrong form must stop the run before anything is written"
        )

    def test_a_rules_file_without_one_rule_element_stops_the_run_and_names_it(self, tmp_path):
        targets = _targets(tmp_path)
        bad = targets.rules_dir / "alpha.md"
        _write(bad, "# Alpha\n\nThis is not tag form.\n")

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

    def _committed(self, tmp_path) -> projection.Targets:
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

    def test_forward_check_builds_the_plan_despite_an_uncommitted_render(self, tmp_path):
        targets = self._committed(tmp_path)
        _write(targets.working_rules, "hand-edited, never committed\n")

        plan = render.build_forward_plan(targets, check=True)

        assert plan.files, (
            "a check that only reads must reach the plan even where a target is dirty, "
            "since it writes nothing that dirty state could put at risk"
        )

    def test_forward_write_refuses_the_same_uncommitted_render(self, tmp_path):
        targets = self._committed(tmp_path)
        _write(targets.working_rules, "hand-edited, never committed\n")

        with pytest.raises(ValueError, match=re.escape("working-rules.md")):
            render.build_forward_plan(targets, check=False)

    def test_reverse_check_builds_the_plan_despite_an_uncommitted_source(self, tmp_path):
        targets = self._committed(tmp_path)
        _write(targets.rules_dir / "alpha.md", f"{_element('alpha', 'Alpha, edited.')}\n")

        plan = render.build_reverse_plan(targets, check=True)

        assert plan.files, (
            "a check that only reads must reach the plan even where a source is dirty"
        )

    def test_reverse_write_refuses_the_same_uncommitted_source(self, tmp_path):
        targets = self._committed(tmp_path)
        _write(targets.rules_dir / "alpha.md", f"{_element('alpha', 'Alpha, edited.')}\n")

        with pytest.raises(ValueError, match=re.escape("alpha.md")):
            render.build_reverse_plan(targets, check=False)


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
        edited = _element("alpha", "Alpha, edited in the render.")
        _write(
            targets.working_rules,
            "\n\n".join([render.TITLE, PREAMBLE, edited, ZETA]) + "\n",
        )

        render.main(["--reverse"], targets=targets)

        assert (targets.rules_dir / "alpha.md").read_text(encoding="utf-8") == f"{edited}\n", (
            "the render is the form the user edits, and the reverse is what carries those edits"
        )
