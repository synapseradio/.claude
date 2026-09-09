#!/usr/bin/env python3
"""Tests for `scripts/agent-configs/own-opencode-key.py`.

Run with `python3.14 -m pytest scripts/tests/test_own_opencode_key.py`.

Every test builds its own tree under a tmp_path and passes a Targets naming
it, so no test reads or writes the real `~/.config/opencode/opencode.json`.
"""

import importlib.util
import json
import pathlib
import subprocess
import sys

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]

sys.path.insert(0, str(REPO_ROOT / "scripts" / "agent-configs"))
import projection  # noqa: E402  (path must be set before this import)

_KEY_PATH = REPO_ROOT / "scripts" / "agent-configs" / "own-opencode-key.py"
_spec = importlib.util.spec_from_file_location("own_opencode_key_test", _KEY_PATH)
assert _spec is not None and _spec.loader is not None
key_owner = importlib.util.module_from_spec(_spec)
sys.modules["own_opencode_key_test"] = key_owner
_spec.loader.exec_module(key_owner)


def _write(path: pathlib.Path, text: str) -> pathlib.Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


PREAMBLE = '<hello from="user">\n~\n/~\n</hello>\n\n<stance>\n\nPlay.\n\n</stance>'


def _element(name: str, body: str) -> str:
    return f'<rule name="{name}">\n\n{body}\n\n</rule>'


ALPHA = _element("alpha", "Alpha holds.")


def _targets(tmp_path: pathlib.Path) -> projection.Targets:
    claude_home = tmp_path / "claude"
    _write(claude_home / "CLAUDE.md", f"{PREAMBLE}\n")
    rules = claude_home / projection.RULES_DIRNAME
    _write(rules / "alpha.md", f"{ALPHA}\n")
    _write(
        rules / "gated.md",
        f'---\npaths:\n  - "**/*.sh"\n---\n\n{_element("gated", "Gated holds.")}\n',
    )
    return projection.Targets(
        claude_home=claude_home,
        pi_home=tmp_path / "pi",
        opencode_home=tmp_path / "opencode",
        working_rules_order=("alpha",),
    )


class TestRuleInstructions:
    def test_names_each_unconditional_rule_under_home(self, tmp_path):
        targets = _targets(tmp_path)

        listed = key_owner.rule_instructions(targets.rules_dir)

        assert any(entry.endswith("alpha.md") for entry in listed), (
            "opencode reads the session-wide rules through this list, so every always-on rule "
            "must name its file in it"
        )


class TestAHandWrittenFileWithOneOwnedKey:
    """`config-projection` requirement: a generated file is owned whole.

    Scenario: A hand-written file with one owned key.
    """

    def test_owned_key_rewrites_and_every_other_key_and_its_order_survive(self, tmp_path):
        targets = _targets(tmp_path)
        hand_written = {
            "$schema": "https://opencode.ai/config.json",
            "instructions": ["stale.md"],
            "theme": "opencode",
            "mcp": {"linkup": {"type": "local"}},
        }
        before_bytes = json.dumps(hand_written, indent=2) + "\n"
        _write(targets.opencode_config, before_bytes)

        assert key_owner.main([], targets=targets) == 0

        after_bytes = targets.opencode_config.read_text(encoding="utf-8")
        after = json.loads(after_bytes)

        assert after["instructions"] != hand_written["instructions"], (
            "the job must rewrite the one key it owns"
        )
        assert any(entry.endswith("alpha.md") for entry in after["instructions"]), (
            "the rewritten key must list the current always-on rules"
        )

        before_without_instructions = dict(hand_written, instructions=after["instructions"])
        expected_bytes = json.dumps(before_without_instructions, indent=2) + "\n"
        assert after_bytes == expected_bytes, (
            "every other key, and the file's key order, must be byte-identical to what a "
            "hand-written file carried before the job ran"
        )


def _git(repo: pathlib.Path, *args: str) -> None:
    """Run one git command in `repo`, with the user's hooks and signing off."""

    subprocess.run(
        ["git", "-C", str(repo), "-c", "core.hooksPath=", "-c", "commit.gpgsign=false", *args],
        check=True,
        capture_output=True,
    )


def _committed(tmp_path: pathlib.Path) -> projection.Targets:
    """The same tree, plus the owned key, committed in one git repository.

    The repository opens at `tmp_path`, so the opencode configuration sits
    inside it and an edit there is work git can report.
    """

    targets = _targets(tmp_path)
    assert key_owner.main([], targets=targets) == 0
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "config", "user.email", "test@example.invalid")
    _git(tmp_path, "config", "user.name", "Test")
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-q", "-m", "the tree as a run last left it")
    return targets


class TestCheckModeReportsDrift:
    """`config-projection` requirement: a check mode reports drift without writing.

    Scenarios: Everything in sync, and One output has drifted.

    The owned key lists the rule files rather than their text, so the drift
    these read is a rule the list does not name.
    """

    def test_check_exits_zero_when_the_key_matches(self, tmp_path):
        targets = _targets(tmp_path)
        key_owner.main([], targets=targets)

        assert key_owner.main(["--check"], targets=targets) == 0, (
            "a key this job just wrote from these rules is by definition in sync"
        )

    def test_check_names_the_key_and_its_file_after_a_rule_is_added(self, tmp_path, capsys):
        targets = _targets(tmp_path)
        key_owner.main([], targets=targets)
        written = targets.opencode_config.read_text(encoding="utf-8")
        _write(targets.rules_dir / "zeta.md", f"{_element('zeta', 'Zeta holds.')}\n")
        capsys.readouterr()

        code = key_owner.main(["--check"], targets=targets)
        printed = capsys.readouterr().out

        assert code != 0, "a rule the list does not name is a rule opencode never loads"
        assert "instructions" in printed and str(targets.opencode_config) in printed, (
            "the check names the key it owns and the file holding it, since the file carries "
            "hand-written keys this job leaves alone"
        )
        assert targets.opencode_config.read_text(encoding="utf-8") == written, (
            "a check reports a difference without repairing it"
        )

    def test_check_exits_nonzero_when_the_file_does_not_exist(self, tmp_path):
        targets = _targets(tmp_path)

        assert key_owner.main(["--check"], targets=targets) != 0, (
            "a key that was never written differs from what a run would produce"
        )
        assert not targets.opencode_config.exists(), "a check writes nothing, the file included"

    def test_check_reports_drift_rather_than_refusing_on_a_dirty_file(self, tmp_path, capsys):
        targets = _committed(tmp_path)
        _write(targets.opencode_config, json.dumps({"instructions": ["hand-edited.md"]}) + "\n")
        capsys.readouterr()

        code = key_owner.main(["--check"], targets=targets)
        printed = capsys.readouterr().out

        assert code != 0, "the key on disk differs from what this job would write"
        assert str(targets.opencode_config) in printed, (
            "a run that writes nothing overwrites nothing, so an uncommitted file is no "
            "reason to report the tree in place of the drift"
        )


class TestBuildPlan:
    def test_opencode_instructions_list_the_unconditional_rules(self, tmp_path):
        targets = _targets(tmp_path)

        plan = key_owner.build_plan(targets)
        owned = {(key.path, key.key): key.value for key in plan.keys}
        listed = owned[(targets.opencode_config, "instructions")]

        assert any(entry.endswith("alpha.md") for entry in listed), (
            "every rule that loads each session must reach opencode"
        )

    def test_opencode_instructions_exclude_a_path_scoped_rule(self, tmp_path):
        targets = _targets(tmp_path)

        plan = key_owner.build_plan(targets)
        owned = {(key.path, key.key): key.value for key in plan.keys}
        listed = owned[(targets.opencode_config, "instructions")]

        assert not any(entry.endswith("gated.md") for entry in listed), (
            "the plugin appends a path-scoped rule when a matching file is in play, so listing it "
            "here would load it in every session and twice in a matching one"
        )
