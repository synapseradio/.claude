#!/usr/bin/env python3
"""Tests for `scripts/agent-configs/translate-for-pi.py`.

Run with `python3.14 -m pytest scripts/tests/test_translate_for_pi.py`.

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


PREAMBLE = '<hello from="user">\n~\n/~\n</hello>\n\n<stance>\n\nPlay.\n\n</stance>'


def _element(name: str, body: str) -> str:
    return f'<rule name="{name}">\n\n{body}\n\n</rule>'


ALPHA = _element("alpha", "Alpha holds.")

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
    rules = claude_home / projection.RULESETS_DIRNAME / projection.DEFAULT_MODEL
    _write(rules / "alpha.md", f"{ALPHA}\n")
    _write(
        rules / "gated.md",
        f'---\npaths:\n  - "**/*.sh"\n---\n\n{_element("gated", "Gated holds.")}\n',
    )
    _write(claude_home / "agents" / "scout.md", AGENT_SOURCE)
    _write(claude_home / "plugins" / "installed_plugins.json", json.dumps({"plugins": {}}))
    _write(claude_home / "settings.json", json.dumps({"enabledPlugins": {}}))
    return projection.Targets(
        claude_home=claude_home,
        pi_home=tmp_path / "pi",
        opencode_home=tmp_path / "opencode",
        working_rules_order=("alpha",),
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
    def test_grants_skills_inheritance(self, tmp_path):
        agent = projection.read_agent(_write(tmp_path / "scout.md", AGENT_SOURCE))

        translated = pi.translate_for_pi(agent)

        assert projection.parse_document(translated.content).frontmatter["inheritSkills"] is True, (
            "pi loads a subagent's skills only when the frontmatter grants it explicitly"
        )


class TestBuildAgentsMarkdown:
    def test_carries_the_preamble_and_the_unconditional_rules(self, tmp_path):
        targets = _targets(tmp_path)

        built = pi.build_agents_markdown(targets.claude_md, targets.rules_dir)

        assert "Play." in built and "Alpha holds." in built, (
            "pi reads one context file per directory, so its copy needs the preamble and every "
            "always-on rule concatenated"
        )


class TestRunningOneJobAlone:
    """`config-projection` requirement: each projection job runs independently.

    Scenario: Running one job (pi translation runs alone; the render,
    opencode's outputs, and the opencode key stay untouched).
    """

    def test_pi_alone_leaves_the_render_opencode_and_the_key_untouched(self, tmp_path):
        targets = _targets(tmp_path)
        working_rules_before = "a render this job must never touch\n"
        opencode_agents_before = "an opencode context file this job must never touch\n"
        opencode_config_before = json.dumps({"instructions": ["untouched"]}, indent=2) + "\n"
        _write(targets.working_rules, working_rules_before)
        _write(targets.opencode_home / "AGENTS.md", opencode_agents_before)
        _write(targets.opencode_config, opencode_config_before)

        assert pi.main([], targets=targets) == 0

        assert (targets.pi_home / "AGENTS.md").is_file(), "the pi job must write its own outputs"
        assert (targets.pi_home / "agents" / "scout.md").is_file(), (
            "the pi job must translate every agent definition into its own directory"
        )
        assert targets.working_rules.read_text(encoding="utf-8") == working_rules_before, (
            "a job invoked alone must leave the working-rules render untouched"
        )
        assert (targets.opencode_home / "AGENTS.md").read_text(
            encoding="utf-8"
        ) == opencode_agents_before, "a job invoked alone must leave opencode's outputs untouched"
        assert targets.opencode_config.read_text(encoding="utf-8") == opencode_config_before, (
            "a job invoked alone must leave the opencode key untouched"
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

    def test_the_plan_carries_that_agent_s_file_alone(self, tmp_path):
        targets = self._two_agents(tmp_path)

        plan = pi.build_one_agent("spider", targets)

        assert {generated.path for generated in plan.files} == {
            targets.pi_home / "agents" / "spider.md"
        }, (
            "a scoped run writes one agent's translation, and pi's context file and the skill "
            "paths belong to no single agent"
        )

    def test_a_scoped_run_leaves_another_agent_s_output_alone(self, tmp_path):
        targets = self._two_agents(tmp_path)
        assert pi.main([], targets=targets) == 0
        scout = targets.pi_home / "agents" / "scout.md"
        scout.write_text("a file this run must never reach\n", encoding="utf-8")

        assert pi.main(["--agent", "spider"], targets=targets) == 0

        assert scout.read_text(encoding="utf-8") == "a file this run must never reach\n", (
            "scoping to one agent is what lets a run repair one translation while another "
            "source is mid-edit"
        )

    def test_a_name_no_source_carries_stops_the_run(self, tmp_path):
        targets = self._two_agents(tmp_path)

        with pytest.raises(SystemExit) as raised:
            pi.main(["--agent", "nobody"], targets=targets)

        assert raised.value.code != 0, (
            "a misspelled name would otherwise write nothing and report success"
        )

    def test_the_check_mode_reports_the_scoped_agent_drifting(self, tmp_path, capsys):
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

    def test_check_exits_zero_when_every_output_matches(self, tmp_path):
        targets = _targets(tmp_path)
        pi.main([], targets=targets)

        assert pi.main(["--check"], targets=targets) == 0, (
            "outputs this job just wrote from these sources are by definition in sync"
        )

    def test_check_names_the_context_file_after_a_rule_body_changes(self, tmp_path, capsys):
        targets = _targets(tmp_path)
        pi.main([], targets=targets)
        context_file = targets.pi_home / "AGENTS.md"
        written = context_file.read_text(encoding="utf-8")
        _write(targets.rules_dir / "alpha.md", f"{_element('alpha', 'Alpha, edited.')}\n")
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

    def test_check_exits_nonzero_when_an_output_is_missing(self, tmp_path):
        targets = _targets(tmp_path)

        assert pi.main(["--check"], targets=targets) != 0, (
            "an output that was never written differs from what a run would produce"
        )
        assert not targets.pi_home.exists(), "a check writes nothing, a target directory included"

    def test_check_reports_drift_rather_than_refusing_on_a_dirty_target(self, tmp_path, capsys):
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

    def test_a_hand_edit_to_a_generated_file_is_rewritten_away(self, tmp_path):
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
        return claude_md, rules

    def test_rule_carrying_paths_frontmatter_stays_out(self, tmp_path):
        claude_md, rules = self._tree(tmp_path)

        built = pi.build_agents_markdown(claude_md, rules)

        assert "Gated {" not in built, (
            "the extension appends a path-scoped rule when a matching file is in play, so "
            "carrying it here would load it in every session and twice in a matching one"
        )
        assert "paths:" not in built, "no frontmatter reaches the context file"

    def test_rule_without_frontmatter_goes_in(self, tmp_path):
        claude_md, rules = self._tree(tmp_path)

        built = pi.build_agents_markdown(claude_md, rules)

        assert "Alpha {\n  always\n}" in built, "a rule with no frontmatter loads every session"
        assert "Zeta {\n  always\n}" in built, "a rule with no frontmatter loads every session"

    def test_preamble_leads_and_rules_follow_in_filename_order(self, tmp_path):
        claude_md, rules = self._tree(tmp_path)

        built = pi.build_agents_markdown(claude_md, rules)

        assert built.index("# Preamble") < built.index("Alpha {") < built.index("Zeta {"), (
            "CLAUDE.md leads and rules follow sorted by filename, so the output is deterministic"
        )

    def test_frontmatter_delimiters_do_not_reach_the_output(self, tmp_path):
        claude_md, rules = self._tree(tmp_path)

        built = pi.build_agents_markdown(claude_md, rules)

        assert "paths:" not in built, "an excluded rule contributes none of its frontmatter either"

    def test_paths_in_rule_bodies_are_rewritten(self, tmp_path):
        claude_md = _write(tmp_path / "CLAUDE.md", "# Preamble\n")
        rules = tmp_path / "rules"
        _write(rules / "alpha.md", "Alpha {\n  read `~/.claude/references/x.md`\n}\n")

        built = pi.build_agents_markdown(claude_md, rules)

        assert "`$HOME/.claude/references/x.md`" in built, (
            "a rule body reaches the generated file through the same path rewrite as the preamble"
        )

    def test_sections_are_separated_by_one_blank_line(self, tmp_path):
        claude_md = _write(tmp_path / "CLAUDE.md", "# Preamble\n\n\n")
        rules = tmp_path / "rules"
        _write(rules / "alpha.md", "Alpha {\n}\n\n\n")
        _write(rules / "zeta.md", "Zeta {\n}\n")

        built = pi.build_agents_markdown(claude_md, rules)

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

    def test_enabled_plugin_with_skills_contributes_its_path(self, tmp_path):
        install = tmp_path / "cache" / "seed" / "software"
        (install / "skills").mkdir(parents=True)
        installed, settings = self._tree(
            tmp_path,
            {"software@seed": True},
            {"software@seed": [{"scope": "user", "installPath": str(install)}]},
        )

        assert pi.resolve_skill_paths(installed, settings) == [str(install / "skills")], (
            "an enabled plugin's skills directory is what the other agents need on their path"
        )

    def test_enabled_plugin_without_skills_contributes_nothing(self, tmp_path):
        install = tmp_path / "cache" / "official" / "typescript-lsp"
        install.mkdir(parents=True)
        installed, settings = self._tree(
            tmp_path,
            {"typescript-lsp@official": True},
            {"typescript-lsp@official": [{"scope": "user", "installPath": str(install)}]},
        )

        assert pi.resolve_skill_paths(installed, settings) == [], (
            "a plugin carrying hooks or MCP servers alone has no skills directory to add"
        )

    def test_disabled_plugin_contributes_nothing(self, tmp_path):
        install = tmp_path / "cache" / "seed" / "switchboard"
        (install / "skills").mkdir(parents=True)
        installed, settings = self._tree(
            tmp_path,
            {"switchboard@seed": False},
            {"switchboard@seed": [{"scope": "user", "installPath": str(install)}]},
        )

        assert pi.resolve_skill_paths(installed, settings) == [], (
            "a disabled plugin's skills stay out, or the other agents load what Claude does not"
        )

    def test_enabled_plugin_missing_from_the_install_record_is_skipped(self, tmp_path):
        installed, settings = self._tree(tmp_path, {"ghost@nowhere": True}, {})

        assert pi.resolve_skill_paths(installed, settings) == [], (
            "an enable naming no installed plugin resolves to no path rather than raising"
        )

    def test_user_scope_wins_over_project_scope(self, tmp_path):
        old = tmp_path / "cache" / "skill-creator" / "1.0.0"
        new = tmp_path / "cache" / "skill-creator" / "2.0.0"
        (old / "skills").mkdir(parents=True)
        (new / "skills").mkdir(parents=True)
        installed, settings = self._tree(
            tmp_path,
            {"skill-creator@official": True},
            {
                "skill-creator@official": [
                    {"scope": "project", "installPath": str(old)},
                    {"scope": "user", "installPath": str(new)},
                ]
            },
        )

        assert pi.resolve_skill_paths(installed, settings) == [str(new / "skills")], (
            "two installed versions of one plugin would put two copies of each skill on the "
            "path, and the user-scoped record is the one a user-level enable turns on"
        )

    def test_project_scope_serves_when_no_user_record_exists(self, tmp_path):
        install = tmp_path / "cache" / "seed" / "visualizer"
        (install / "skills").mkdir(parents=True)
        installed, settings = self._tree(
            tmp_path,
            {"visualizer@seed": True},
            {"visualizer@seed": [{"scope": "project", "installPath": str(install)}]},
        )

        assert pi.resolve_skill_paths(installed, settings) == [str(install / "skills")], (
            "a plugin installed only against a project still resolves to one install path"
        )

    def test_paths_come_back_sorted(self, tmp_path):
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

        assert resolved == sorted(resolved), (
            "the order must not follow the JSON key order, or the output churns between runs"
        )


class TestTranslateForPiFrontmatter:
    def test_model_stays_a_bare_tier_name(self, tmp_path):
        agent = projection.read_agent(_agent_definition(tmp_path, "scout", model="haiku"))

        translated = pi.translate_for_pi(agent)

        assert projection.parse_document(translated.content).frontmatter["model"] == "haiku", (
            "pi resolves a tier name through its own model catalog"
        )

    def test_absent_model_emits_no_model_key(self, tmp_path):
        agent = projection.read_agent(_agent_definition(tmp_path, "orchestrator"))

        translated = pi.translate_for_pi(agent)

        assert "model:" not in translated.content, (
            "emitting a model key where the source names none would pin an agent "
            "that should inherit"
        )

    def test_tools_render_comma_separated(self, tmp_path):
        agent = projection.read_agent(
            _agent_definition(tmp_path, "scout", tools="Read, Grep, Bash")
        )

        translated = pi.translate_for_pi(agent)

        assert (
            projection.parse_document(translated.content).frontmatter["tools"] == "read, grep, bash"
        ), "pi reads tools as one comma-separated string, not as a map"

    def test_glob_maps_to_find(self, tmp_path):
        agent = projection.read_agent(_agent_definition(tmp_path, "scout", tools="Glob"))

        translated = pi.translate_for_pi(agent)

        assert projection.parse_document(translated.content).frontmatter["tools"] == "find", (
            "pi's find takes a glob pattern, which is what Claude's Glob does"
        )

    def test_tools_pi_lacks_drop_and_are_reported(self, tmp_path):
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

    def test_absent_tools_emits_no_tools_key(self, tmp_path):
        agent = projection.read_agent(_agent_definition(tmp_path, "orchestrator"))

        translated = pi.translate_for_pi(agent)

        assert "tools:" not in translated.content, (
            "an empty tools list would grant no tools, where the source granted every tool"
        )

    def test_body_becomes_the_system_prompt_unchanged(self, tmp_path):
        agent = projection.read_agent(_agent_definition(tmp_path, "scout", model="sonnet"))

        translated = pi.translate_for_pi(agent)

        assert projection.parse_document(translated.content).body == AGENT_BODY, (
            "the body is the system prompt and no rewrite applies to it"
        )


class TestBuildPlan:
    def test_pi_agents_markdown_carries_the_preamble_and_the_unconditional_rules(self, tmp_path):
        targets = _targets(tmp_path)

        plan = pi.build_plan(targets)
        by_path = {f.path: f.content for f in plan.files}
        written = by_path[targets.pi_home / "AGENTS.md"]

        assert "<stance>" in written, "pi reads the CLAUDE.md preamble from its context file"
        assert ALPHA in written, (
            "pi offers no second mechanism for rule files, so the rules travel in its context file"
        )
        assert "gated" not in written, (
            "a path-scoped rule reaches pi through the extension when a matching file is in play, "
            "so carrying it here would load it in every session and twice in a matching one"
        )

    def test_build_plan_writes_no_copy_of_a_path_scoped_rule(self, tmp_path):
        plan = pi.build_plan(_targets(tmp_path))

        assert not any(f.path.name == "gated.md" for f in plan.files), (
            "the plugin reads a path-scoped rule from its canonical file and strips the "
            "frontmatter itself, so no copy exists to fall out of date"
        )

    def test_every_source_agent_yields_one_file_under_pi(self, tmp_path):
        targets = _targets(tmp_path)
        _agent_definition(targets.agents_dir, "orchestrator")

        plan = pi.build_plan(targets)
        paths = {f.path for f in plan.files}

        assert {
            targets.pi_home / "agents" / "scout.md",
            targets.pi_home / "agents" / "orchestrator.md",
        } <= paths, "each source agent must reach this target"

    def test_skill_paths_render_as_a_paths_object(self, tmp_path):
        targets = _targets(tmp_path)

        plan = pi.build_plan(targets)
        by_path = {f.path: f.content for f in plan.files}
        written = json.loads(by_path[targets.skill_paths_file])

        assert list(written) == ["paths"], (
            "the consumer merging these reads a single paths key and nothing else"
        )

    def test_dropped_tools_are_reported_per_agent(self, tmp_path):
        plan = pi.build_plan(_targets(tmp_path))

        assert plan.dropped == (("pi", "scout", "Agent"),), (
            "pi carries no subagent tool, so scout's Agent grant cannot cross and must be named"
        )


class TestApply:
    def test_first_run_creates_missing_parent_directories(self, tmp_path):
        targets = _targets(tmp_path)
        assert not targets.pi_home.exists(), "the fixture starts with no pi root"

        pi.main([], targets=targets)

        assert (targets.pi_home / "agents" / "scout.md").is_file(), (
            "a target directory that does not exist yet must be created rather than skipped"
        )

    def test_second_run_reports_no_change(self, tmp_path, capsys):
        targets = _targets(tmp_path)
        pi.main([], targets=targets)
        capsys.readouterr()

        pi.main([], targets=targets)
        printed = capsys.readouterr().out

        assert "created" not in printed and "updated" not in printed, (
            "generating twice from unchanged sources must be a no-op, or the output is not "
            "a function of the sources alone"
        )

    def test_check_leaves_a_stale_file_stale(self, tmp_path):
        targets = _targets(tmp_path)
        pi.main([], targets=targets)
        stale = targets.pi_home / "AGENTS.md"
        _write(stale, "hand-edited\n")

        pi.main(["--check"], targets=targets)

        assert stale.read_text(encoding="utf-8") == "hand-edited\n", (
            "--check reports a difference without repairing it"
        )
