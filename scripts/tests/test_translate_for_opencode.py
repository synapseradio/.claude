#!/usr/bin/env -S uv run --frozen
"""Tests for `scripts/agent-configs/translate-for-opencode.py`.

Run with `.venv/bin/python -m pytest scripts/tests/test_translate_for_opencode.py`.

Every test builds its own tree under a tmp_path and passes a Targets naming
it, so no test reads or writes this checkout's own configuration or pi's or
opencode's real directories.
"""

import importlib.util
import json
import pathlib
import subprocess
import sys
import types

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]

sys.path.insert(0, str(REPO_ROOT / "scripts" / "agent-configs"))
import projection  # noqa: E402  (path must be set before this import)


def _load(name: str, filename: str) -> types.ModuleType:
    path = REPO_ROOT / "scripts" / "agent-configs" / filename
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


opencode = _load("translate_for_opencode_test", "translate-for-opencode.py")


def _write(path: pathlib.Path, text: str) -> pathlib.Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


PREAMBLE = "# Preamble\n\nPlay."


def _body(stem: str, body: str) -> str:
    return f"<!-- rule: {stem} -->\n\n## {stem}\n\n{body}"


ALPHA = _body("alpha", "Alpha holds.")


def _agent_source(model: str = "haiku", tools: str = "Read, Glob, Agent") -> str:
    return (
        "---\n"
        "name: scout\n"
        "description: scouts the codebase.\n"
        f"model: {model}\n"
        f"tools: {tools}\n"
        "---\n\n"
        "Scout body.\n"
    )


def _targets(tmp_path: pathlib.Path, *, model: str = "haiku") -> projection.Targets:
    claude_home = tmp_path / "claude"
    _write(claude_home / "CLAUDE.md", f"{PREAMBLE}\n")
    _write(claude_home / "rulesets" / "rules" / "alpha.md", f"{ALPHA}\n")
    _write(claude_home / "agents" / "scout.md", _agent_source(model=model))
    _write(claude_home / "plugins" / "installed_plugins.json", json.dumps({"plugins": {}}))
    _write(claude_home / "settings.json", json.dumps({"enabledPlugins": {}}))
    return projection.Targets(
        claude_home=claude_home,
        pi_home=tmp_path / "pi",
        opencode_home=tmp_path / "opencode",
        rulesets_dir=claude_home / "rulesets",
    )


class TestTranslateForOpencode:
    def test_carries_the_subagent_mode(self, tmp_path) -> None:
        agent = projection.read_agent(_write(tmp_path / "scout.md", _agent_source()))

        translated = opencode.translate_for_opencode(agent)

        assert projection.parse_document(translated.content).frontmatter["mode"] == "subagent", (
            "every translated agent runs as an opencode subagent"
        )


def _git(repo: pathlib.Path, *args: str) -> None:
    """Run one git command in `repo`, with the user's hooks and signing off."""
    subprocess.run(
        ["git", "-C", str(repo), "-c", "core.hooksPath=", "-c", "commit.gpgsign=false", *args],
        check=True,
        capture_output=True,
    )


def _committed(tmp_path: pathlib.Path) -> projection.Targets:
    """The same tree, plus opencode's outputs, committed in one git repository.

    The repository opens at `tmp_path`, so opencode's target directory sits
    inside it and an edit there is work git can report.
    """
    targets = _targets(tmp_path)
    assert opencode.main([], targets=targets) == 0
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "config", "user.email", "test@example.invalid")
    _git(tmp_path, "config", "user.name", "Test")
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-q", "-m", "the tree as a run last left it")
    return targets


class TestScopingToOneAgent:
    """A run scoped to one agent translates that source and reads no other."""

    def _two_agents(self, tmp_path: pathlib.Path) -> projection.Targets:
        targets = _targets(tmp_path)
        _write(
            targets.agents_dir / "spider.md",
            _agent_source().replace("scout", "spider").replace("Scout", "Spider"),
        )
        return targets

    def test_a_scoped_run_leaves_another_agent_s_output_and_the_preamble_alone(
        self, tmp_path
    ) -> None:
        targets = self._two_agents(tmp_path)
        assert opencode.main([], targets=targets) == 0
        scout = targets.opencode_home / "agents" / "scout.md"
        context_file = targets.opencode_home / "AGENTS.md"
        scout.write_text("a file this run must never reach\n", encoding="utf-8")
        context_file.write_text("a file this run must never reach either\n", encoding="utf-8")

        assert opencode.main(["--agent", "spider"], targets=targets) == 0

        assert scout.read_text(encoding="utf-8") == "a file this run must never reach\n", (
            "scoping to one agent is what lets a run repair one translation while another "
            "source is mid-edit"
        )
        assert (
            context_file.read_text(encoding="utf-8") == "a file this run must never reach either\n"
        ), "a scoped run leaves AGENTS.md as it stands, since the preamble derives from no agent"
        assert (targets.opencode_home / "agents" / "spider.md").is_file(), (
            "the scoped run writes the one agent it names"
        )

    def test_a_name_no_source_carries_stops_the_run(self, tmp_path) -> None:
        targets = self._two_agents(tmp_path)

        with pytest.raises(SystemExit) as raised:
            opencode.main(["--agent", "nobody"], targets=targets)

        assert raised.value.code != 0, (
            "a misspelled name would otherwise write nothing and report success"
        )

    def test_the_check_mode_reports_the_scoped_agent_drifting(self, tmp_path, capsys) -> None:
        targets = self._two_agents(tmp_path)
        assert opencode.main([], targets=targets) == 0
        _write(targets.agents_dir / "spider.md", _agent_source().replace("scout", "spider"))
        capsys.readouterr()

        code = opencode.main(["--agent", "spider", "--check"], targets=targets)
        printed = capsys.readouterr().out

        assert code != 0, "the source changed, so the translation on disk no longer matches it"
        assert "spider.md" in printed and "scout.md" not in printed, (
            "a scoped check reports the one agent it was scoped to"
        )


class TestCheckModeReportsDrift:
    """`config-projection` requirement: a check mode reports drift without writing.

    Scenarios: Everything in sync, and One output has drifted.

    This job's outputs carry the `CLAUDE.md` preamble and the agent
    definitions. A rule body reaches opencode through the `instructions` key
    another job owns, so the drift these read is a change to a source this
    job does read.
    """

    def test_check_exits_zero_when_every_output_matches(self, tmp_path) -> None:
        targets = _targets(tmp_path)
        opencode.main([], targets=targets)

        assert opencode.main(["--check"], targets=targets) == 0, (
            "outputs this job just wrote from these sources are by definition in sync"
        )

    @pytest.mark.parametrize(
        ("source", "output", "edit"),
        [
            pytest.param(
                "CLAUDE.md",
                "AGENTS.md",
                lambda targets: _write(
                    targets.claude_md, f"{PREAMBLE}\n\n## What wins\n\nNearness decides.\n"
                ),
                id="the preamble",
            ),
            pytest.param(
                "agents/scout.md",
                "agents/scout.md",
                lambda targets: _write(
                    targets.agents_dir / "scout.md", _agent_source(model="sonnet")
                ),
                id="an agent definition",
            ),
        ],
    )
    def test_check_names_the_output_after_its_source_changes(
        self, tmp_path, capsys, source, output, edit
    ) -> None:
        targets = _targets(tmp_path)
        opencode.main([], targets=targets)
        generated = targets.opencode_home / output
        written = generated.read_text(encoding="utf-8")
        edit(targets)
        capsys.readouterr()

        code = opencode.main(["--check"], targets=targets)
        printed = capsys.readouterr().out

        assert code != 0, f"a change to {source} that never reached its output is drift"
        assert str(generated) in printed, (
            "a check that reports drift without naming the path leaves the reader hunting "
            "for which of the outputs moved"
        )
        assert generated.read_text(encoding="utf-8") == written, (
            "a check reports a difference without repairing it"
        )

    def test_check_exits_nonzero_when_an_output_is_missing(self, tmp_path) -> None:
        targets = _targets(tmp_path)

        assert opencode.main(["--check"], targets=targets) != 0, (
            "an output that was never written differs from what a run would produce"
        )
        assert not targets.opencode_home.exists(), (
            "a check writes nothing, a target directory included"
        )

    def test_check_reports_drift_rather_than_refusing_on_a_dirty_target(
        self, tmp_path, capsys
    ) -> None:
        targets = _committed(tmp_path)
        dirty = targets.opencode_home / "AGENTS.md"
        _write(dirty, "hand-edited, never committed\n")
        capsys.readouterr()

        code = opencode.main(["--check"], targets=targets)
        printed = capsys.readouterr().out

        assert code != 0, "the file on disk differs from what this job would write"
        assert str(dirty) in printed, (
            "a run that writes nothing overwrites nothing, so an uncommitted target is no "
            "reason to report the tree in place of the drift"
        )


class TestAGeneratedFileIsOwnedWhole:
    """`config-projection` requirement: a generated file is owned whole."""

    def test_a_hand_edit_to_a_generated_file_is_rewritten_away(self, tmp_path) -> None:
        targets = _targets(tmp_path)
        opencode.main([], targets=targets)
        agent_file = targets.opencode_home / "agents" / "scout.md"
        generated = agent_file.read_text(encoding="utf-8")
        _write(agent_file, generated + "\nA hand-written paragraph nobody generated.\n")

        opencode.main([], targets=targets)

        assert agent_file.read_text(encoding="utf-8") == generated, (
            "this job rewrites each file it generates in full, so hand-written content in one "
            "of them survives no run and belongs in a file the job does not own"
        )


AGENT_BODY = "Scout {\n  Options {\n    budget: 1..200 = 40\n  }\n}\n"


def _agent_definition(directory: pathlib.Path, name: str, **keys: str) -> pathlib.Path:
    lines = [f"name: {name}", "description: Use this agent to scout, and to report."]
    lines += [f"{key}: {value}" for key, value in keys.items()]
    frontmatter = "\n".join(lines)
    return _write(directory / f"{name}.md", f"---\n{frontmatter}\n---\n\n{AGENT_BODY}")


class TestTranslateForOpencodeFrontmatter:
    def test_model_tier_becomes_a_provider_id(self, tmp_path) -> None:
        agent = projection.read_agent(_agent_definition(tmp_path, "scout", model="haiku"))

        translated = opencode.translate_for_opencode(agent)

        assert "model: anthropic/claude-haiku-4-5" in translated.content, (
            "opencode names a model by provider/model id, not by Claude's tier name"
        )

    def test_tools_become_a_lowercase_map_with_agent_as_task(self, tmp_path) -> None:
        agent = projection.read_agent(
            _agent_definition(tmp_path, "scout", tools="Read, Grep, Glob, Bash, Agent")
        )

        translated = opencode.translate_for_opencode(agent)
        frontmatter = projection.parse_document(translated.content).frontmatter

        assert frontmatter["tools"] == {
            "read": True,
            "grep": True,
            "glob": True,
            "bash": True,
            "task": True,
        }, (
            "opencode reads tools as a map of its own lowercase tool names to booleans, and "
            "spawns subagents through `task`, which is what Claude's Agent names"
        )
        assert translated.dropped == (), "every tool in this grant crosses, so none is dropped"

    def test_claude_only_tools_drop_and_are_reported(self, tmp_path) -> None:
        agent = projection.read_agent(
            _agent_definition(
                tmp_path, "spider", tools="Bash, ToolSearch, mcp__linkup__linkup-search"
            )
        )

        translated = opencode.translate_for_opencode(agent)
        frontmatter = projection.parse_document(translated.content).frontmatter

        assert frontmatter["tools"] == {"bash": True}, (
            "a tool opencode does not carry must not reach its frontmatter under any name"
        )
        assert translated.dropped == ("ToolSearch", "mcp__linkup__linkup-search"), (
            "a dropped tool narrows the agent's reach, so the run must name what it dropped"
        )

    def test_a_source_naming_no_model_and_no_tools_emits_neither_key(self, tmp_path) -> None:
        agent = projection.read_agent(_agent_definition(tmp_path, "orchestrator"))

        translated = opencode.translate_for_opencode(agent)

        assert "model:" not in translated.content, (
            "emitting a model key where the source names none would pin an agent "
            "that should inherit"
        )
        assert "tools:" not in translated.content, (
            "an empty tools map would grant no tools, where the source granted every tool"
        )

    def test_description_and_body_carry_across_unchanged(self, tmp_path) -> None:
        agent = projection.read_agent(_agent_definition(tmp_path, "scout", model="haiku"))

        translated = opencode.translate_for_opencode(agent)
        document = projection.parse_document(translated.content)

        assert document.frontmatter["description"] == "Use this agent to scout, and to report.", (
            "the description is what a router matches on, so it must carry across unchanged"
        )
        assert document.body == AGENT_BODY, "the body is the system prompt and no rewrite applies"


class TestWhatAFullRunWrites:
    def test_agents_md_carries_the_preamble_alone_and_each_source_agent_gets_a_file(
        self, tmp_path
    ) -> None:
        targets = _targets(tmp_path)
        _agent_definition(targets.agents_dir, "orchestrator")

        assert opencode.main([], targets=targets) == 0

        written = (targets.opencode_home / "AGENTS.md").read_text(encoding="utf-8")
        assert "Play." in written and "Alpha holds." not in written, (
            "opencode reads the always-on rules through the instructions key another job owns, "
            "so repeating them in AGENTS.md would load them twice"
        )
        for name in ("scout", "orchestrator"):
            assert (targets.opencode_home / "agents" / f"{name}.md").is_file(), (
                f"each source agent must reach opencode: {name}"
            )
