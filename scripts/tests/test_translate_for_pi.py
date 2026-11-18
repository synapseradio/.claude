#!/usr/bin/env python3
"""Tests for `scripts/agent-configs/translate-for-pi.py`.

Run with `.venv/bin/python -m pytest scripts/tests/test_translate_for_pi.py`.

Every test builds its own tree under a tmp_path and passes a Targets naming
it, so no test reads or writes this checkout's own configuration or pi's or
opencode's real directories.
"""

import importlib.util
import json
import pathlib
import subprocess
import sys

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]

sys.path.insert(0, str(REPO_ROOT / "scripts" / "agent-configs"))
import projection  # noqa: E402  (path must be set before this import)

_PI_PATH = REPO_ROOT / "scripts" / "agent-configs" / "translate-for-pi.py"
_spec = importlib.util.spec_from_file_location("translate_for_pi_test", _PI_PATH)
assert _spec is not None and _spec.loader is not None
pi = importlib.util.module_from_spec(_spec)
sys.modules["translate_for_pi_test"] = pi
_spec.loader.exec_module(pi)


def _write(path: pathlib.Path, text: str) -> pathlib.Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


PREAMBLE = "# Preamble\n\nPlay."


def _body(stem: str, body: str) -> str:
    return f"<!-- rule: {stem} -->\n\n## {stem}\n\n{body}"


ALPHA = _body("alpha", "Alpha holds.")

AGENT_SOURCE = (
    "---\n"
    "name: scout\n"
    "description: scouts the codebase.\n"
    "model: haiku\n"
    "tools: Read, Glob, Agent\n"
    "---\n\n"
    "Scout body.\n"
)


def _targets(tmp_path: pathlib.Path) -> projection.Targets:
    claude_home = tmp_path / "claude"
    _write(claude_home / "CLAUDE.md", f"{PREAMBLE}\n")
    rules = claude_home / "rulesets" / "rules"
    _write(rules / "alpha.md", f"{ALPHA}\n")
    _write(
        rules / "gated.md",
        f'---\npaths:\n  - "**/*.sh"\n---\n\n{_body("gated", "Gated holds.")}\n',
    )
    _write(claude_home / "agents" / "scout.md", AGENT_SOURCE)
    _write(claude_home / "plugins" / "installed_plugins.json", json.dumps({"plugins": {}}))
    _write(claude_home / "settings.json", json.dumps({"enabledPlugins": {}}))
    return projection.Targets(
        claude_home=claude_home,
        pi_home=tmp_path / "pi",
        opencode_home=tmp_path / "opencode",
        rulesets_dir=claude_home / "rulesets",
    )


def _git(repo: pathlib.Path, *args: str) -> None:
    """Run one git command in `repo`, with the user's hooks and signing off."""
    subprocess.run(
        ["git", "-C", str(repo), "-c", "core.hooksPath=", "-c", "commit.gpgsign=false", *args],
        check=True,
        capture_output=True,
    )


def _committed(tmp_path: pathlib.Path) -> projection.Targets:
    """The same tree, plus pi's outputs, committed in one git repository.

    The repository opens at `tmp_path`, so pi's target directory sits inside
    it and an edit there is work git can report.
    """
    targets = _targets(tmp_path)
    assert pi.main([], targets=targets) == 0
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "config", "user.email", "test@example.invalid")
    _git(tmp_path, "config", "user.name", "Test")
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-q", "-m", "the tree as a run last left it")
    return targets


class TestTranslateForPi:
    def test_grants_skills_inheritance(self, tmp_path) -> None:
        agent = projection.read_agent(_write(tmp_path / "scout.md", AGENT_SOURCE))

        translated = pi.translate_for_pi(agent)

        assert projection.parse_document(translated.content).frontmatter["inheritSkills"] is True, (
            "pi loads a subagent's skills only when the frontmatter grants it explicitly"
        )


class TestScopingToOneAgent:
    """A run scoped to one agent translates that source and reads no other."""

    def _two_agents(self, tmp_path: pathlib.Path) -> projection.Targets:
        targets = _targets(tmp_path)
        _write(
            targets.agents_dir / "spider.md",
            AGENT_SOURCE.replace("scout", "spider").replace("Scout", "Spider"),
        )
        return targets

    def test_a_scoped_run_leaves_another_agent_s_output_and_the_context_files_alone(
        self, tmp_path
    ) -> None:
        targets = self._two_agents(tmp_path)
        assert pi.main([], targets=targets) == 0
        scout = targets.pi_home / "agents" / "scout.md"
        context_file = targets.pi_home / "AGENTS.md"
        scout.write_text("a file this run must never reach\n", encoding="utf-8")
        context_file.write_text("a file this run must never reach either\n", encoding="utf-8")

        assert pi.main(["--agent", "spider"], targets=targets) == 0

        assert scout.read_text(encoding="utf-8") == "a file this run must never reach\n", (
            "scoping to one agent is what lets a run repair one translation while another "
            "source is mid-edit"
        )
        assert (
            context_file.read_text(encoding="utf-8") == "a file this run must never reach either\n"
        ), "a scoped run leaves AGENTS.md as it stands, since it derives from no single agent"
        assert (targets.pi_home / "agents" / "spider.md").is_file(), (
            "the scoped run writes the one agent it names"
        )

    def test_a_name_no_source_carries_stops_the_run(self, tmp_path) -> None:
        targets = self._two_agents(tmp_path)

        with pytest.raises(SystemExit) as raised:
            pi.main(["--agent", "nobody"], targets=targets)

        assert raised.value.code != 0, (
            "a misspelled name would otherwise write nothing and report success"
        )

    def test_the_check_mode_reports_the_scoped_agent_drifting(self, tmp_path, capsys) -> None:
        targets = self._two_agents(tmp_path)
        assert pi.main([], targets=targets) == 0
        _write(targets.agents_dir / "spider.md", AGENT_SOURCE.replace("scout", "spider"))
        capsys.readouterr()

        code = pi.main(["--agent", "spider", "--check"], targets=targets)
        printed = capsys.readouterr().out

        assert code != 0, "the source changed, so the translation on disk no longer matches it"
        assert "spider.md" in printed and "scout.md" not in printed, (
            "a scoped check reports the one agent it was scoped to"
        )


class TestCheckModeReportsDrift:
    """`config-projection` requirement: a check mode reports drift without writing.

    Scenarios: Everything in sync, and One output has drifted.
    """

    def test_check_exits_zero_when_every_output_matches(self, tmp_path) -> None:
        targets = _targets(tmp_path)
        pi.main([], targets=targets)

        assert pi.main(["--check"], targets=targets) == 0, (
            "outputs this job just wrote from these sources are by definition in sync"
        )

    def test_check_names_the_context_file_after_a_rule_body_changes(self, tmp_path, capsys) -> None:
        targets = _targets(tmp_path)
        pi.main([], targets=targets)
        context_file = targets.pi_home / "AGENTS.md"
        written = context_file.read_text(encoding="utf-8")
        _write(targets.rulesets_dir / "rules" / "alpha.md", f"{_body('alpha', 'Alpha, edited.')}\n")
        capsys.readouterr()

        code = pi.main(["--check"], targets=targets)
        printed = capsys.readouterr().out

        assert code != 0, (
            "pi reads the rule bodies from its one context file, so an edited body that "
            "never reached it is drift"
        )
        assert str(context_file) in printed, (
            "a check that reports drift without naming the path leaves the reader hunting "
            "for which of the outputs moved"
        )
        assert context_file.read_text(encoding="utf-8") == written, (
            "a check reports a difference without repairing it"
        )

    def test_check_exits_nonzero_when_an_output_is_missing(self, tmp_path) -> None:
        targets = _targets(tmp_path)

        assert pi.main(["--check"], targets=targets) != 0, (
            "an output that was never written differs from what a run would produce"
        )
        assert not targets.pi_home.exists(), "a check writes nothing, a target directory included"

    def test_check_reports_drift_rather_than_refusing_on_a_dirty_target(
        self, tmp_path, capsys
    ) -> None:
        targets = _committed(tmp_path)
        dirty = targets.pi_home / "AGENTS.md"
        _write(dirty, "hand-edited, never committed\n")
        capsys.readouterr()

        code = pi.main(["--check"], targets=targets)
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
        pi.main([], targets=targets)
        context_file = targets.pi_home / "AGENTS.md"
        generated = context_file.read_text(encoding="utf-8")
        _write(context_file, generated + "\nA hand-written paragraph nobody generated.\n")

        pi.main([], targets=targets)

        assert context_file.read_text(encoding="utf-8") == generated, (
            "this job rewrites each file it generates in full, so hand-written content in one "
            "of them survives no run and belongs in a file the job does not own"
        )


AGENT_BODY = "Scout {\n  Options {\n    budget: 1..200 = 40\n  }\n}\n"


def _agent_definition(tmp_path: pathlib.Path, name: str, **keys: str) -> pathlib.Path:
    lines = [f"name: {name}", "description: Use this agent to scout, and to report."]
    lines += [f"{key}: {value}" for key, value in keys.items()]
    frontmatter = "\n".join(lines)
    return _write(tmp_path / f"{name}.md", f"---\n{frontmatter}\n---\n\n{AGENT_BODY}")


class TestBuildAgentsMarkdownFromASourceTree:
    def _tree(self, tmp_path: pathlib.Path) -> tuple[pathlib.Path, pathlib.Path]:
        claude_md = _write(tmp_path / "CLAUDE.md", "# Preamble\n\nStance goes here.\n")
        rules = tmp_path / "rules"
        _write(rules / "alpha.md", "Alpha {\n  always\n}\n")
        _write(
            rules / "gated.md",
            '---\npaths:\n  - "**/*.sh"\n---\n\nGated {\n  sometimes\n}\n',
        )
        _write(rules / "zeta.md", "Zeta {\n  always\n}\n")
        return claude_md, tmp_path

    def test_the_preamble_leads_then_each_always_on_rule_in_filename_order_and_no_gated_rule(
        self, tmp_path
    ) -> None:
        claude_md, rulesets = self._tree(tmp_path)

        built = pi.build_agents_markdown(claude_md, rulesets)

        assert built.index("# Preamble") < built.index("Alpha {") < built.index("Zeta {"), (
            "CLAUDE.md leads and rules follow sorted by filename, so the output is deterministic"
        )
        assert "Gated {" not in built and "paths:" not in built, (
            "the extension appends a path-scoped rule when a matching file is in play, so "
            "carrying it here would load it in every session and twice in a matching one"
        )

    def test_paths_in_rule_bodies_are_rewritten(self, tmp_path) -> None:
        claude_md = _write(tmp_path / "CLAUDE.md", "# Preamble\n")
        rulesets = tmp_path
        rules = rulesets / "rules"
        _write(rules / "alpha.md", "Alpha {\n  read `~/.claude/references/x.md`\n}\n")

        built = pi.build_agents_markdown(claude_md, rulesets)

        assert "`$HOME/.claude/references/x.md`" in built, (
            "a rule body reaches the generated file through the same path rewrite as the preamble"
        )

    def test_sections_are_separated_by_one_blank_line(self, tmp_path) -> None:
        claude_md = _write(tmp_path / "CLAUDE.md", "# Preamble\n\n\n")
        rulesets = tmp_path
        rules = rulesets / "rules"
        _write(rules / "alpha.md", "Alpha {\n}\n\n\n")
        _write(rules / "zeta.md", "Zeta {\n}\n")

        built = pi.build_agents_markdown(claude_md, rulesets)

        assert built == "# Preamble\n\nAlpha {\n}\n\nZeta {\n}\n", (
            "trailing blank lines in a source must not vary the joint, or the output stops "
            "being a function of the rule text alone"
        )


class TestResolveSkillPaths:
    def _tree(self, tmp_path, enabled: dict, plugins: dict) -> tuple[pathlib.Path, pathlib.Path]:
        installed = _write(
            tmp_path / "installed_plugins.json",
            json.dumps({"version": 2, "plugins": plugins}),
        )
        settings = _write(tmp_path / "settings.json", json.dumps({"enabledPlugins": enabled}))
        return installed, settings

    @pytest.mark.parametrize(
        ("enabled", "has_skills", "listed", "contributes"),
        [
            pytest.param(True, True, True, True, id="an enabled plugin with skills"),
            pytest.param(True, False, True, False, id="an enabled plugin carrying no skills"),
            pytest.param(False, True, True, False, id="a disabled plugin"),
            pytest.param(True, True, False, False, id="an enable naming no installed plugin"),
        ],
    )
    def test_only_an_enabled_installed_plugin_with_skills_contributes_its_path(
        self, tmp_path, enabled, has_skills, listed, contributes
    ) -> None:
        install = tmp_path / "cache" / "seed" / "software"
        install.mkdir(parents=True)
        if has_skills:
            (install / "skills").mkdir()
        records = [{"scope": "user", "installPath": str(install)}] if listed else []
        installed, settings = self._tree(
            tmp_path, {"software@seed": enabled}, {"software@seed": records} if listed else {}
        )

        assert pi.resolve_skill_paths(installed, settings) == (
            [str(install / "skills")] if contributes else []
        ), "pi gains the skills of what Claude has enabled, and nothing Claude does not load"

    def test_one_install_path_per_plugin_with_user_scope_ahead_of_project(self, tmp_path) -> None:
        old = tmp_path / "cache" / "skill-creator" / "1.0.0"
        new = tmp_path / "cache" / "skill-creator" / "2.0.0"
        only = tmp_path / "cache" / "visualizer"
        for directory in (old, new, only):
            (directory / "skills").mkdir(parents=True)
        installed, settings = self._tree(
            tmp_path,
            {"skill-creator@official": True, "visualizer@seed": True},
            {
                "skill-creator@official": [
                    {"scope": "project", "installPath": str(old)},
                    {"scope": "user", "installPath": str(new)},
                ],
                "visualizer@seed": [{"scope": "project", "installPath": str(only)}],
            },
        )

        assert pi.resolve_skill_paths(installed, settings) == sorted(
            [str(new / "skills"), str(only / "skills")]
        ), (
            "two installed versions of one plugin would put two copies of each skill on the "
            "path, and the user-scoped record is the one a user-level enable turns on; a "
            "plugin installed only against a project still resolves"
        )

    def test_paths_come_back_sorted_whatever_the_key_order(self, tmp_path) -> None:
        for name in ("zeta", "alpha"):
            (tmp_path / "cache" / name / "skills").mkdir(parents=True)
        installed, settings = self._tree(
            tmp_path,
            {"zeta@seed": True, "alpha@seed": True},
            {
                "zeta@seed": [{"scope": "user", "installPath": str(tmp_path / "cache" / "zeta")}],
                "alpha@seed": [{"scope": "user", "installPath": str(tmp_path / "cache" / "alpha")}],
            },
        )

        resolved = pi.resolve_skill_paths(installed, settings)

        assert resolved == sorted(resolved) and len(resolved) == 2, (
            "the order must not follow the JSON key order, or the output churns between runs"
        )


class TestTranslateForPiFrontmatter:
    def test_model_stays_a_bare_tier_name(self, tmp_path) -> None:
        agent = projection.read_agent(_agent_definition(tmp_path, "scout", model="haiku"))

        translated = pi.translate_for_pi(agent)

        assert projection.parse_document(translated.content).frontmatter["model"] == "haiku", (
            "pi resolves a tier name through its own model catalog"
        )

    def test_a_source_naming_no_model_and_no_tools_emits_neither_key(self, tmp_path) -> None:
        agent = projection.read_agent(_agent_definition(tmp_path, "orchestrator"))

        translated = pi.translate_for_pi(agent)

        assert "model:" not in translated.content, (
            "emitting a model key where the source names none would pin an agent "
            "that should inherit"
        )
        assert "tools:" not in translated.content, (
            "an empty tools list would grant no tools, where the source granted every tool"
        )

    def test_tools_render_comma_separated_with_glob_as_find(self, tmp_path) -> None:
        agent = projection.read_agent(
            _agent_definition(tmp_path, "scout", tools="Read, Grep, Bash, Glob")
        )

        translated = pi.translate_for_pi(agent)

        assert (
            projection.parse_document(translated.content).frontmatter["tools"]
            == "read, grep, bash, find"
        ), "pi reads tools as one comma-separated string, and its find takes Claude's Glob patterns"

    def test_tools_pi_lacks_drop_and_are_reported(self, tmp_path) -> None:
        agent = projection.read_agent(
            _agent_definition(tmp_path, "skill-designer", tools="Read, Agent, ToolSearch")
        )

        translated = pi.translate_for_pi(agent)

        assert projection.parse_document(translated.content).frontmatter["tools"] == "read", (
            "pi carries bash, read, edit, write, grep, find, and ls, and nothing else"
        )
        assert translated.dropped == ("Agent", "ToolSearch"), (
            "a dropped tool narrows the agent's reach, so the run must name what it dropped"
        )

    def test_body_carries_across_unchanged_and_skills_inheritance_is_granted(
        self, tmp_path
    ) -> None:
        agent = projection.read_agent(_agent_definition(tmp_path, "scout", model="sonnet"))

        translated = pi.translate_for_pi(agent)
        document = projection.parse_document(translated.content)

        assert document.body == AGENT_BODY, "the body is the system prompt and no rewrite applies"
        assert document.frontmatter["inheritSkills"] is True, (
            "pi loads a subagent's skills only when the frontmatter grants it explicitly"
        )


class TestWhatAFullRunWrites:
    def test_one_context_file_one_file_per_source_agent_and_the_skill_paths_and_nothing_else(
        self, tmp_path
    ) -> None:
        targets = _targets(tmp_path)
        _agent_definition(targets.agents_dir, "orchestrator")

        plan = pi.build_plan(targets)

        assert {f.path for f in plan.files} == {
            targets.pi_home / "AGENTS.md",
            targets.pi_home / "agents" / "scout.md",
            targets.pi_home / "agents" / "orchestrator.md",
            targets.skill_paths_file,
        }, (
            "each source agent reaches pi, and a path-scoped rule gets no copy of its own, since "
            "the plugin reads it from its canonical file and no copy exists to fall out of date"
        )

    def test_the_skill_paths_file_holds_a_single_paths_key(self, tmp_path) -> None:
        targets = _targets(tmp_path)

        plan = pi.build_plan(targets)
        written = json.loads({f.path: f.content for f in plan.files}[targets.skill_paths_file])

        assert list(written) == ["paths"], (
            "the consumer merging these reads a single paths key and nothing else"
        )
