#!/usr/bin/env python3
"""Tests for the shared library at `scripts/agent-configs/projection.py`.

Run with `python3.14 -m pytest scripts/tests/test_projection.py`.

Every test builds its own tree under a tmp_path, so no test writes outside
that directory or reads this checkout's own configuration.
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

_SYNC_PATH = REPO_ROOT / "scripts" / "sync-agent-configs.py"
_spec = importlib.util.spec_from_file_location("sync_agent_configs_projection_test", _SYNC_PATH)
assert _spec is not None and _spec.loader is not None
sync = importlib.util.module_from_spec(_spec)
sys.modules["sync_agent_configs_projection_test"] = sync
_spec.loader.exec_module(sync)


def _write(path: pathlib.Path, text: str) -> pathlib.Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


PREAMBLE = '<hello from="user">\n~\n/~\n</hello>\n\n<stance>\n\nPlay.\n\n</stance>'


def _element(name: str, body: str) -> str:
    return f'<rule name="{name}">\n\n{body}\n\n</rule>'


ALPHA = _element("alpha", "Alpha holds.")


def _git(repo: pathlib.Path, *args: str) -> None:
    """Run one git command in `repo`, with the user's hooks and signing off."""

    subprocess.run(
        ["git", "-C", str(repo), "-c", "core.hooksPath=", "-c", "commit.gpgsign=false", *args],
        check=True,
        capture_output=True,
    )


class TestRulesSourceIsNamedOnce:
    """`config-projection` requirement: one place names the rules source."""

    def test_two_jobs_read_one_source(self, tmp_path):
        claude_md = _write(tmp_path / "CLAUDE.md", f"{PREAMBLE}\n")
        rules_dir = tmp_path / "not-called-rules"
        _write(rules_dir / "alpha.md", f"{ALPHA}\n")

        rendered = sync.build_working_rules(claude_md, rules_dir, ("alpha",))
        agents_markdown = sync.build_agents_markdown(claude_md, rules_dir)

        assert "Alpha holds." in rendered, (
            "the render must read the rule body from the directory its caller names, "
            "which fails the moment the render names one of its own"
        )
        assert "Alpha holds." in agents_markdown, (
            "pi's context file must read the same rule body from the same directory, "
            "which fails the moment that job names a directory of its own"
        )

    def test_the_source_directory_moves(self, tmp_path):
        tree_a = tmp_path / "a"
        _write(tree_a / "CLAUDE.md", f"{PREAMBLE}\n")
        _write(tree_a / "rules" / "alpha.md", f"{ALPHA}\n")

        tree_b = tmp_path / "b"
        _write(tree_b / "CLAUDE.md", f"{PREAMBLE}\n")
        _write(tree_b / "rulesets" / "default" / "alpha.md", f"{ALPHA}\n")

        targets_a = projection.Targets(
            claude_home=tree_a,
            pi_home=tmp_path / "pi-a",
            opencode_home=tmp_path / "opencode-a",
            rules_dirname="rules",
            working_rules_order=("alpha",),
        )
        targets_b = projection.Targets(
            claude_home=tree_b,
            pi_home=tmp_path / "pi-b",
            opencode_home=tmp_path / "opencode-b",
            rules_dirname="rulesets/default",
            working_rules_order=("alpha",),
        )

        rendered_a = sync.build_working_rules(
            targets_a.claude_md, targets_a.rules_dir, targets_a.working_rules_order
        )
        rendered_b = sync.build_working_rules(
            targets_b.claude_md, targets_b.rules_dir, targets_b.working_rules_order
        )
        assert rendered_a == rendered_b, (
            "moving the named directory to a different path holding the same bodies "
            "must not change the render by one byte"
        )

        agents_a = sync.build_agents_markdown(targets_a.claude_md, targets_a.rules_dir)
        agents_b = sync.build_agents_markdown(targets_b.claude_md, targets_b.rules_dir)
        assert agents_a == agents_b, (
            "moving the named directory must not change pi's context file by one byte either"
        )


class TestRefusesToOverwriteUncommittedWork:
    """`config-projection` requirement: a job refuses to overwrite uncommitted work."""

    def _repo(self, tmp_path) -> pathlib.Path:
        repo = tmp_path / "repo"
        repo.mkdir()
        _git(repo, "init", "-q")
        _git(repo, "config", "user.email", "test@example.invalid")
        _git(repo, "config", "user.name", "Test")
        return repo

    def test_a_target_carries_uncommitted_changes(self, tmp_path):
        repo = self._repo(tmp_path)
        target = _write(repo / "working-rules.md", "committed body\n")
        _git(repo, "add", "-A")
        _git(repo, "commit", "-q", "-m", "the tree as a run last left it")
        _write(target, "edited after the commit\n")

        with pytest.raises(ValueError, match=re.escape("working-rules.md")) as raised:
            projection.refuse_uncommitted(repo, [target])

        assert "these carry uncommitted changes this run would overwrite" in str(raised.value), (
            "a job that would write over an uncommitted edit must write nothing and name the file"
        )

    def test_an_untracked_target(self, tmp_path):
        repo = self._repo(tmp_path)
        _git(repo, "commit", "-q", "-m", "empty root commit", "--allow-empty")
        target = _write(repo / "AGENTS.md", "never added to git\n")

        with pytest.raises(ValueError, match=re.escape("AGENTS.md")) as raised:
            projection.refuse_uncommitted(repo, [target])

        assert "these carry uncommitted changes this run would overwrite" in str(raised.value), (
            "a file git has never seen is exactly as unrecoverable as one it has seen "
            "change, so the refusal applies and names it the same way"
        )
