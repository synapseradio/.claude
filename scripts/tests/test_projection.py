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


def _load(name: str, filename: str):
    path = REPO_ROOT / "scripts" / "agent-configs" / filename
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


# The two jobs the "Two jobs read one source" scenario names, each loaded the
# way its own test file loads it.
render = _load("render_working_rules_via_projection_test", "render-working-rules.py")
pi = _load("translate_for_pi_via_projection_test", "translate-for-pi.py")


def _write(path: pathlib.Path, text: str) -> pathlib.Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


PREAMBLE = '<hello from="user">\n~\n/~\n</hello>\n\n<stance>\n\nPlay.\n\n</stance>'


def _element(name: str, body: str) -> str:
    return f'<rule name="{name}">\n\n{body}\n\n</rule>'


ALPHA = _element("alpha", "Alpha holds.")
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


class TestRulesSourceIsNamedOnce:
    """`config-projection` requirement: one place names the rules source."""

    def test_two_jobs_read_one_source(self, tmp_path):
        claude_md = _write(tmp_path / "CLAUDE.md", f"{PREAMBLE}\n")
        rules_dir = tmp_path / "not-called-rules"
        _write(rules_dir / "alpha.md", f"{ALPHA}\n")

        rendered = render.build_working_rules(claude_md, rules_dir, ("alpha",))
        agents_markdown = pi.build_agents_markdown(claude_md, rules_dir)

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
        _write(tree_a / "some-other-root" / "default" / "alpha.md", f"{ALPHA}\n")

        tree_b = tmp_path / "b"
        _write(tree_b / "CLAUDE.md", f"{PREAMBLE}\n")
        _write(tree_b / "rulesets" / "haiku" / "alpha.md", f"{ALPHA}\n")

        targets_a = projection.Targets(
            claude_home=tree_a,
            pi_home=tmp_path / "pi-a",
            opencode_home=tmp_path / "opencode-a",
            rulesets_dirname="some-other-root",
            working_rules_order=("alpha",),
        )
        targets_b = projection.Targets(
            claude_home=tree_b,
            pi_home=tmp_path / "pi-b",
            opencode_home=tmp_path / "opencode-b",
            model="haiku",
            working_rules_order=("alpha",),
        )

        rendered_a = render.build_working_rules(
            targets_a.claude_md, targets_a.rules_dir, targets_a.working_rules_order
        )
        rendered_b = render.build_working_rules(
            targets_b.claude_md, targets_b.rules_dir, targets_b.working_rules_order
        )
        assert rendered_a == rendered_b, (
            "moving the named directory to a different path holding the same bodies "
            "must not change the render by one byte"
        )

        agents_a = pi.build_agents_markdown(targets_a.claude_md, targets_a.rules_dir)
        agents_b = pi.build_agents_markdown(targets_b.claude_md, targets_b.rules_dir)
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


class TestParseDocument:
    def test_frontmatter_block_separates_from_body(self):
        text = "---\nname: scout\nmodel: haiku\n---\n\nScout {\n  budget: 40\n}\n"

        doc = projection.parse_document(text)

        assert doc.frontmatter == {"name": "scout", "model": "haiku"}, (
            "a leading --- block must parse as YAML frontmatter"
        )
        assert doc.body == "Scout {\n  budget: 40\n}\n", (
            "the body must be the text after the closing ---, with the blank separator dropped"
        )

    def test_file_without_frontmatter_reports_none(self):
        text = "CoreRules {\n  AppliesWhen { every context }\n}\n"

        doc = projection.parse_document(text)

        assert doc.frontmatter is None, (
            "a file opening on something other than --- carries no frontmatter"
        )
        assert doc.body == text, "the whole text is the body when no frontmatter opens the file"

    def test_horizontal_rule_mid_file_is_not_frontmatter(self):
        text = "Some prose\n\n---\n\nmore prose\n"

        doc = projection.parse_document(text)

        assert doc.frontmatter is None, (
            "a --- that is not the first line opens no frontmatter block"
        )


class TestRewritePaths:
    def test_tilde_prefix_becomes_the_home_variable(self):
        rewritten = projection.rewrite_paths(
            "read `~/.claude/references/bash-style-guide.md` in full"
        )

        assert rewritten == "read `$HOME/.claude/references/bash-style-guide.md` in full", (
            "a ~/ prefix must resolve, since the generated file sits where ~ is not expanded"
        )

    def test_no_output_names_the_running_user(self):
        rewritten = projection.rewrite_paths(
            "`~/.claude/x` and [y](./rules/y.md) and `../.dotfiles/z`"
        )

        assert str(HOME) not in rewritten, (
            "the active home directory must reach no generated byte, since a name baked "
            "into a committed file breaks on every other machine"
        )

    def test_bare_tilde_survives(self):
        text = "<hello>\n~\nHi!\n/~\n</hello>\n"

        assert projection.rewrite_paths(text) == text, (
            "a ~ that starts no path is decoration and must survive byte for byte"
        )

    def test_relative_link_target_resolves_against_the_home_variable(self):
        rewritten = projection.rewrite_paths(
            "live in [core-rules.md](./rules/core-rules.md) and load"
        )

        assert rewritten == (
            "live in [core-rules.md]($HOME/.claude/rules/core-rules.md) and load"
        ), "a link relative to ~/.claude does not resolve from the directory the output sits in"

    def test_parent_relative_link_target_resolves(self):
        rewritten = projection.rewrite_paths("see [x](../.dotfiles/git/ignore)")

        assert rewritten == "see [x]($HOME/.dotfiles/git/ignore)", (
            "a ../ segment must collapse rather than survive into the resolved path"
        )

    def test_home_variable_link_survives(self):
        text = "at [x]($HOME/.claude/rules/core-rules.md)"

        assert projection.rewrite_paths(text) == text, (
            "a target already naming $HOME must not resolve a second time against ~/.claude"
        )

    def test_url_link_survives(self):
        text = "per [Peirce](https://plato.stanford.edu/entries/peirce/)"

        assert projection.rewrite_paths(text) == text, "an http(s) target names no file on disk"

    def test_anchor_link_survives(self):
        text = "see [above](#precedence)"

        assert projection.rewrite_paths(text) == text, "a fragment target names no file on disk"

    def test_absolute_link_survives(self):
        text = f"at [x]({HOME}/.claude/rules/core-rules.md)"

        assert projection.rewrite_paths(text) == text, "an already-absolute target needs no rewrite"

    def test_prose_around_a_rewrite_survives_byte_for_byte(self):
        text = "Alpha `~/.claude/x` beta\n\n- gamma: delta\n  - epsilon\n"

        assert (
            projection.rewrite_paths(text)
            == "Alpha `$HOME/.claude/x` beta\n\n- gamma: delta\n  - epsilon\n"
        ), "only the path token changes; every other byte, newline and indent included, survives"


class TestRestorePaths:
    def test_home_variable_becomes_a_tilde_prefix(self):
        restored = projection.restore_paths(
            "read `$HOME/.claude/references/bash-style-guide.md` in full"
        )

        assert restored == "read `~/.claude/references/bash-style-guide.md` in full", (
            "a source file sits where ~ expands, so the variable the render carries goes back"
        )

    def test_link_target_inside_claude_home_becomes_dot_relative(self):
        restored = projection.restore_paths(
            "live in [core-rules.md]($HOME/.claude/rules/core-rules.md)"
        )

        assert restored == "live in [core-rules.md](./rules/core-rules.md)", (
            "a source names a sibling under ~/.claude by the ./ form the forward run resolves"
        )

    def test_link_target_outside_claude_home_becomes_parent_relative(self):
        restored = projection.restore_paths("see [x]($HOME/.dotfiles/git/ignore)")

        assert restored == "see [x](../.dotfiles/git/ignore)", (
            "a target under the home directory but outside ~/.claude climbs one level"
        )

    def test_url_link_survives(self):
        text = "per [Peirce](https://plato.stanford.edu/entries/peirce/)"

        assert projection.restore_paths(text) == text, "an http(s) target names no file on disk"

    def test_anchor_link_survives(self):
        text = "see [above](#precedence)"

        assert projection.restore_paths(text) == text, "a fragment target names no file on disk"

    def test_absolute_link_outside_the_home_directory_survives(self):
        text = "at [x](/etc/hosts)"

        assert projection.restore_paths(text) == text, (
            "a path outside the home directory has no relative form under ~/.claude"
        )

    def test_bare_tilde_and_dollar_survive(self):
        text = "<hello>\n~\nHi!\n/~\n</hello>\n\n`$dir/$slug__$DD-MM-YY-HHmm.md`\n"

        assert projection.restore_paths(text) == text, (
            "a ~ that starts no path and a $ that opens no HOME are text, not paths"
        )

    def test_restore_inverts_rewrite(self):
        source = (
            "<hello>\n~\n/~\n</hello>\n\n"
            "The rules live in [core-rules.md](./rules/core-rules.md) and load.\n\n"
            "The ignore at `~/.dotfiles/git/ignore` covers it, per [x](../.dotfiles/git/ignore).\n\n"
            "Read `~/.claude/references/bash-style-guide.md`, per "
            "[Peirce](https://plato.stanford.edu/entries/peirce/) and [above](#precedence).\n"
        )

        assert projection.restore_paths(projection.rewrite_paths(source)) == source, (
            "a render that does not restore to its own sources drifts a little on every sync"
        )


class TestReadAgent:
    def test_absent_tools_key_reads_as_every_tool(self, tmp_path):
        agent = projection.read_agent(_agent_source(tmp_path, "orchestrator"))

        assert agent.tools is None, (
            "a source naming no tools grants every tool, which differs from granting none"
        )

    def test_comma_separated_tools_split_into_names(self, tmp_path):
        agent = projection.read_agent(_agent_source(tmp_path, "scout", tools="Read, Grep, Glob"))

        assert agent.tools == ("Read", "Grep", "Glob"), (
            "the source writes tools as one comma-separated string"
        )

    def test_absent_model_reads_as_none(self, tmp_path):
        agent = projection.read_agent(_agent_source(tmp_path, "orchestrator"))

        assert agent.model is None, "a source naming no model inherits the caller's model"


class TestDefaultTargets:
    def test_claude_home_is_the_checkout_the_script_lives_in(self):
        assert projection.DEFAULT_TARGETS.claude_home == REPO_ROOT, (
            "a run reads and writes the checkout it was invoked from, so a hook in a worktree "
            "syncs that worktree and needs no argument naming it"
        )

    def test_the_render_resolves_under_that_checkout(self):
        assert (
            projection.DEFAULT_TARGETS.working_rules
            == REPO_ROOT / "references" / "default" / "working-rules.md"
        ), (
            "the render this repository's pre-push gate compares is the one tracked beside the "
            "sources, under the name of the model whose bodies produced it"
        )
