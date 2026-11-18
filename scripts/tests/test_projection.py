#!/usr/bin/env python3
"""Tests for the shared library at `scripts/agent-configs/projection.py`.

Run with `.venv/bin/python -m pytest scripts/tests/test_projection.py`.

Every test builds its own tree under a tmp_path, so no test writes outside
that directory or reads this checkout's own configuration.
"""

import pathlib
import re
import subprocess
import sys

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]

sys.path.insert(0, str(REPO_ROOT / "scripts" / "agent-configs"))
import projection  # noqa: E402  (path must be set before this import)


def _write(path: pathlib.Path, text: str) -> pathlib.Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


PREAMBLE = "# Preamble\n\nPlay."


def _body(stem: str, body: str) -> str:
    return f"<!-- rule: {stem} -->\n\n## {stem}\n\n{body}"


ALPHA = _body("alpha", "Alpha holds.")
HOME = pathlib.Path.home()

AGENT_BODY = "Scout {\n  Options {\n    budget: 1..200 = 40\n  }\n}\n"


def _agent_source(tmp_path: pathlib.Path, name: str, **keys: str) -> pathlib.Path:
    lines = [f"name: {name}", "description: Use this agent to scout, and to report."]
    lines += [f"{key}: {value}" for key, value in keys.items()]
    frontmatter = "\n".join(lines)
    return _write(tmp_path / f"{name}.md", f"---\n{frontmatter}\n---\n\n{AGENT_BODY}")


def _git(repo: pathlib.Path, *args: str) -> None:
    """Run one git command in `repo`, with the user's hooks and signing off."""
    subprocess.run(
        ["git", "-C", str(repo), "-c", "core.hooksPath=", "-c", "commit.gpgsign=false", *args],
        check=True,
        capture_output=True,
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

    def test_a_target_carries_uncommitted_changes(self, tmp_path) -> None:
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

    def test_an_untracked_target(self, tmp_path) -> None:
        repo = self._repo(tmp_path)
        _git(repo, "commit", "-q", "-m", "empty root commit", "--allow-empty")
        target = _write(repo / "AGENTS.md", "never added to git\n")

        with pytest.raises(ValueError, match=re.escape("AGENTS.md")) as raised:
            projection.refuse_uncommitted(repo, [target])

        assert "these carry uncommitted changes this run would overwrite" in str(raised.value), (
            "a file git has never seen is exactly as unrecoverable as one it has seen "
            "change, so the refusal applies and names it the same way"
        )


REWRITES = [
    pytest.param(
        "read `~/.claude/references/bash-style-guide.md` in full",
        "read `$HOME/.claude/references/bash-style-guide.md` in full",
        id="a tilde prefix becomes the home variable",
    ),
    pytest.param(
        "live in [core-rules.md](./rules/core-rules.md) and load",
        "live in [core-rules.md]($HOME/.claude/rules/core-rules.md) and load",
        id="a relative link resolves against the home variable",
    ),
    pytest.param(
        "see [x](../.dotfiles/git/ignore)",
        "see [x]($HOME/.dotfiles/git/ignore)",
        id="a parent-relative link collapses",
    ),
    pytest.param(
        "Alpha `~/.claude/x` beta\n\n- gamma: delta\n  - epsilon\n",
        "Alpha `$HOME/.claude/x` beta\n\n- gamma: delta\n  - epsilon\n",
        id="the prose around a rewrite survives byte for byte",
    ),
]

UNTOUCHED = [
    pytest.param("~\nHi!\n/~\n", id="a bare tilde"),
    pytest.param("per [Peirce](https://plato.stanford.edu/entries/peirce/)", id="a url link"),
    pytest.param("see [above](#precedence)", id="an anchor link"),
]


class TestRewritePaths:
    @pytest.mark.parametrize(("text", "expected"), REWRITES)
    def test_a_path_only_valid_inside_the_checkout_resolves_against_the_home_variable(
        self, text, expected
    ) -> None:
        assert projection.rewrite_paths(text) == expected, (
            "the generated file sits where ~ is not expanded and a link relative to ~/.claude "
            "points at nothing, so the reference must resolve against $HOME, which names the "
            "same directory on any account"
        )

    @pytest.mark.parametrize(
        "text",
        [
            *UNTOUCHED,
            pytest.param("at [x]($HOME/.claude/rules/core-rules.md)", id="a home-variable link"),
            pytest.param(f"at [x]({HOME}/.claude/rules/core-rules.md)", id="an absolute link"),
        ],
    )
    def test_a_reference_that_needs_no_rewrite_survives(self, text) -> None:
        assert projection.rewrite_paths(text) == text


class TestRestorePaths:
    @pytest.mark.parametrize(
        ("text", "expected"),
        [
            pytest.param(
                "read `$HOME/.claude/references/bash-style-guide.md` in full",
                "read `~/.claude/references/bash-style-guide.md` in full",
                id="the home variable becomes a tilde prefix",
            ),
            pytest.param(
                "live in [core-rules.md]($HOME/.claude/rules/core-rules.md)",
                "live in [core-rules.md](./rules/core-rules.md)",
                id="a link inside the checkout becomes dot-relative",
            ),
            pytest.param(
                "see [x]($HOME/.dotfiles/git/ignore)",
                "see [x](../.dotfiles/git/ignore)",
                id="a link outside the checkout but under home climbs one level",
            ),
        ],
    )
    def test_a_rendered_reference_returns_to_the_form_a_source_carries(
        self, text, expected
    ) -> None:
        assert projection.restore_paths(text) == expected, (
            "a source file sits inside ~/.claude, where ~ expands and links resolve against it"
        )

    @pytest.mark.parametrize(
        "text",
        [
            *UNTOUCHED,
            pytest.param("at [x](/etc/hosts)", id="an absolute link outside home"),
            pytest.param("`$dir/$slug__$DD-MM-YY-HHmm.md`\n", id="a dollar that opens no HOME"),
        ],
    )
    def test_text_that_names_no_rendered_path_survives(self, text) -> None:
        assert projection.restore_paths(text) == text

    def test_restore_inverts_rewrite(self) -> None:
        source = (
            "~\n/~\n\n"
            "The rules live in [core-rules.md](./rules/core-rules.md) and load.\n\n"
            "The ignore at `~/.dotfiles/git/ignore` covers it, per [x](../.dotfiles/git/ignore).\n\n"
            "Read `~/.claude/references/bash-style-guide.md`, per "
            "[Peirce](https://plato.stanford.edu/entries/peirce/) and [above](#precedence).\n"
        )

        assert projection.restore_paths(projection.rewrite_paths(source)) == source, (
            "a render that does not restore to its own sources drifts a little on every sync"
        )


class TestReadAgent:
    def test_a_source_naming_no_tools_grants_every_tool_and_no_model_inherits(
        self, tmp_path
    ) -> None:
        agent = projection.read_agent(_agent_source(tmp_path, "orchestrator"))

        assert agent.tools is None, (
            "a source naming no tools grants every tool, which differs from granting none"
        )
        assert agent.model is None, "a source naming no model inherits the caller's model"

    def test_comma_separated_tools_split_into_names(self, tmp_path) -> None:
        agent = projection.read_agent(_agent_source(tmp_path, "scout", tools="Read, Grep, Glob"))

        assert agent.tools == ("Read", "Grep", "Glob"), (
            "the source writes tools as one comma-separated string"
        )


class TestDefaultTargets:
    def test_claude_home_is_the_checkout_the_script_lives_in(self) -> None:
        assert projection.DEFAULT_TARGETS.claude_home == REPO_ROOT, (
            "a run reads and writes the checkout it was invoked from, so a hook in a worktree "
            "syncs that worktree and needs no argument naming it"
        )
