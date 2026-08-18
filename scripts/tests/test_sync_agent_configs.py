#!/usr/bin/env python3
"""Tests for the agent-config generator under `scripts/sync-agent-configs.py`.

Run with `python3.14 -m pytest scripts/tests/test_sync_agent_configs.py`.

Every test builds its own source tree under a tmp_path and points the
generator at it, so no test reads or writes the real `~/.claude`,
`~/.pi`, or `~/.config/opencode`.
"""

import importlib.util
import json
import pathlib
import sys

import pytest

SCRIPT_PATH = pathlib.Path(__file__).resolve().parents[1] / "sync-agent-configs.py"

_spec = importlib.util.spec_from_file_location("sync_agent_configs", SCRIPT_PATH)
assert _spec is not None and _spec.loader is not None
sync = importlib.util.module_from_spec(_spec)
sys.modules["sync_agent_configs"] = sync
_spec.loader.exec_module(sync)

HOME = pathlib.Path.home()


class TestParseDocument:
    def test_frontmatter_block_separates_from_body(self):
        text = "---\nname: scout\nmodel: haiku\n---\n\nScout {\n  budget: 40\n}\n"

        doc = sync.parse_document(text)

        assert doc.frontmatter == {"name": "scout", "model": "haiku"}, (
            "a leading --- block must parse as YAML frontmatter"
        )
        assert doc.body == "Scout {\n  budget: 40\n}\n", (
            "the body must be the text after the closing ---, with the blank separator dropped"
        )

    def test_file_without_frontmatter_reports_none(self):
        text = "CoreRules {\n  Applies { every context }\n}\n"

        doc = sync.parse_document(text)

        assert doc.frontmatter is None, (
            "a file opening on something other than --- carries no frontmatter"
        )
        assert doc.body == text, "the whole text is the body when no frontmatter opens the file"

    def test_horizontal_rule_mid_file_is_not_frontmatter(self):
        text = "Some prose\n\n---\n\nmore prose\n"

        doc = sync.parse_document(text)

        assert doc.frontmatter is None, (
            "a --- that is not the first line opens no frontmatter block"
        )


class TestRewritePaths:
    def test_tilde_prefix_becomes_the_home_directory(self):
        rewritten = sync.rewrite_paths("read `~/.claude/references/bash-style-guide.md` in full")

        assert rewritten == f"read `{HOME}/.claude/references/bash-style-guide.md` in full", (
            "a ~/ prefix must resolve, since the generated file sits where ~ is not expanded"
        )

    def test_bare_tilde_survives(self):
        text = "<hello>\n~\nHi!\n/~\n</hello>\n"

        assert sync.rewrite_paths(text) == text, (
            "a ~ that starts no path is decoration and must survive byte for byte"
        )

    def test_relative_link_target_becomes_absolute(self):
        rewritten = sync.rewrite_paths("live in [core-rules.md](./rules/core-rules.md) and load")

        assert rewritten == (
            f"live in [core-rules.md]({HOME}/.claude/rules/core-rules.md) and load"
        ), "a link relative to ~/.claude does not resolve from the directory the output sits in"

    def test_parent_relative_link_target_resolves(self):
        rewritten = sync.rewrite_paths("see [x](../.dotfiles/git/ignore)")

        assert rewritten == f"see [x]({HOME}/.dotfiles/git/ignore)", (
            "a ../ segment must collapse rather than survive into the absolute path"
        )

    def test_url_link_survives(self):
        text = "per [Peirce](https://plato.stanford.edu/entries/peirce/)"

        assert sync.rewrite_paths(text) == text, "an http(s) target names no file on disk"

    def test_anchor_link_survives(self):
        text = "see [above](#precedence)"

        assert sync.rewrite_paths(text) == text, "a fragment target names no file on disk"

    def test_absolute_link_survives(self):
        text = f"at [x]({HOME}/.claude/rules/core-rules.sudolang.md)"

        assert sync.rewrite_paths(text) == text, "an already-absolute target needs no rewrite"

    def test_prose_around_a_rewrite_survives_byte_for_byte(self):
        text = "Alpha `~/.claude/x` beta\n\n- gamma: delta\n  - epsilon\n"

        assert (
            sync.rewrite_paths(text)
            == f"Alpha `{HOME}/.claude/x` beta\n\n- gamma: delta\n  - epsilon\n"
        ), "only the path token changes; every other byte, newline and indent included, survives"


def _write(path: pathlib.Path, text: str) -> pathlib.Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


class TestBuildAgentsMarkdown:
    def _tree(self, tmp_path: pathlib.Path) -> tuple[pathlib.Path, pathlib.Path]:
        claude_md = _write(tmp_path / "CLAUDE.md", "# Preamble\n\nStance goes here.\n")
        rules = tmp_path / "rules"
        _write(rules / "alpha.sudolang.md", "Alpha {\n  always\n}\n")
        _write(
            rules / "gated.sudolang.md",
            '---\npaths:\n  - "**/*.sh"\n---\n\nGated {\n  sometimes\n}\n',
        )
        _write(rules / "zeta.sudolang.md", "Zeta {\n  always\n}\n")
        return claude_md, rules

    def test_rule_carrying_paths_frontmatter_stays_out(self, tmp_path):
        claude_md, rules = self._tree(tmp_path)

        built = sync.build_agents_markdown(claude_md, rules)

        assert "Gated {" not in built, (
            "the extension appends a path-scoped rule when a matching file is in play, so "
            "carrying it here would load it in every session and twice in a matching one"
        )
        assert "paths:" not in built, "no frontmatter reaches the context file"

    def test_rule_without_frontmatter_goes_in(self, tmp_path):
        claude_md, rules = self._tree(tmp_path)

        built = sync.build_agents_markdown(claude_md, rules)

        assert "Alpha {\n  always\n}" in built, "a rule with no frontmatter loads every session"
        assert "Zeta {\n  always\n}" in built, "a rule with no frontmatter loads every session"

    def test_preamble_leads_and_rules_follow_in_filename_order(self, tmp_path):
        claude_md, rules = self._tree(tmp_path)

        built = sync.build_agents_markdown(claude_md, rules)

        assert built.index("# Preamble") < built.index("Alpha {") < built.index("Zeta {"), (
            "CLAUDE.md leads and rules follow sorted by filename, so the output is deterministic"
        )

    def test_frontmatter_delimiters_do_not_reach_the_output(self, tmp_path):
        claude_md, rules = self._tree(tmp_path)

        built = sync.build_agents_markdown(claude_md, rules)

        assert "paths:" not in built, "an excluded rule contributes none of its frontmatter either"

    def test_paths_in_rule_bodies_are_rewritten(self, tmp_path):
        claude_md = _write(tmp_path / "CLAUDE.md", "# Preamble\n")
        rules = tmp_path / "rules"
        _write(rules / "alpha.sudolang.md", "Alpha {\n  read `~/.claude/references/x.md`\n}\n")

        built = sync.build_agents_markdown(claude_md, rules)

        assert f"`{HOME}/.claude/references/x.md`" in built, (
            "a rule body reaches the generated file through the same path rewrite as the preamble"
        )

    def test_sections_are_separated_by_one_blank_line(self, tmp_path):
        claude_md = _write(tmp_path / "CLAUDE.md", "# Preamble\n\n\n")
        rules = tmp_path / "rules"
        _write(rules / "alpha.sudolang.md", "Alpha {\n}\n\n\n")
        _write(rules / "zeta.sudolang.md", "Zeta {\n}\n")

        built = sync.build_agents_markdown(claude_md, rules)

        assert built == "# Preamble\n\nAlpha {\n}\n\nZeta {\n}\n", (
            "trailing blank lines in a source must not vary the joint, or the output stops "
            "being a function of the rule text alone"
        )


AGENT_BODY = "Scout {\n  Options {\n    budget: 1..200 = 40\n  }\n}\n"


def _agent_source(tmp_path: pathlib.Path, name: str, **keys: str) -> pathlib.Path:
    lines = [f"name: {name}", "description: Use this agent to scout, and to report."]
    lines += [f"{key}: {value}" for key, value in keys.items()]
    frontmatter = "\n".join(lines)
    return _write(tmp_path / f"{name}.md", f"---\n{frontmatter}\n---\n\n{AGENT_BODY}")


class TestReadAgent:
    def test_absent_tools_key_reads_as_every_tool(self, tmp_path):
        agent = sync.read_agent(_agent_source(tmp_path, "orchestrator"))

        assert agent.tools is None, (
            "a source naming no tools grants every tool, which differs from granting none"
        )

    def test_comma_separated_tools_split_into_names(self, tmp_path):
        agent = sync.read_agent(_agent_source(tmp_path, "scout", tools="Read, Grep, Glob"))

        assert agent.tools == ("Read", "Grep", "Glob"), (
            "the source writes tools as one comma-separated string"
        )

    def test_absent_model_reads_as_none(self, tmp_path):
        agent = sync.read_agent(_agent_source(tmp_path, "orchestrator"))

        assert agent.model is None, "a source naming no model inherits the caller's model"


class TestTranslateForOpencode:
    def test_model_tier_becomes_a_provider_id(self, tmp_path):
        agent = sync.read_agent(_agent_source(tmp_path, "scout", model="haiku"))

        translated = sync.translate_for_opencode(agent)

        assert "model: anthropic/claude-haiku-4-5" in translated.content, (
            "opencode names a model by provider/model id, not by Claude's tier name"
        )

    def test_absent_model_emits_no_model_key(self, tmp_path):
        agent = sync.read_agent(_agent_source(tmp_path, "orchestrator"))

        translated = sync.translate_for_opencode(agent)

        assert "model:" not in translated.content, (
            "emitting a model key where the source names none would pin an agent "
            "that should inherit"
        )

    def test_tools_become_a_lowercase_map_to_true(self, tmp_path):
        agent = sync.read_agent(_agent_source(tmp_path, "scout", tools="Read, Grep, Glob, Bash"))

        translated = sync.translate_for_opencode(agent)
        frontmatter = sync.parse_document(translated.content).frontmatter

        assert frontmatter["tools"] == {
            "read": True,
            "grep": True,
            "glob": True,
            "bash": True,
        }, "opencode reads tools as a map of its own lowercase tool names to booleans"

    def test_agent_tool_maps_to_task(self, tmp_path):
        agent = sync.read_agent(_agent_source(tmp_path, "skill-designer", tools="Read, Agent"))

        translated = sync.translate_for_opencode(agent)
        frontmatter = sync.parse_document(translated.content).frontmatter

        assert frontmatter["tools"] == {"read": True, "task": True}, (
            "opencode spawns subagents through `task`, which is what Claude's Agent names"
        )

    def test_claude_only_tools_drop_and_are_reported(self, tmp_path):
        agent = sync.read_agent(
            _agent_source(tmp_path, "spider", tools="Bash, ToolSearch, mcp__linkup__linkup-search")
        )

        translated = sync.translate_for_opencode(agent)
        frontmatter = sync.parse_document(translated.content).frontmatter

        assert frontmatter["tools"] == {"bash": True}, (
            "a tool opencode does not carry must not reach its frontmatter under any name"
        )
        assert translated.dropped == ("ToolSearch", "mcp__linkup__linkup-search"), (
            "a dropped tool narrows the agent's reach, so the run must name what it dropped"
        )

    def test_absent_tools_emits_no_tools_key(self, tmp_path):
        agent = sync.read_agent(_agent_source(tmp_path, "orchestrator"))

        translated = sync.translate_for_opencode(agent)

        assert "tools:" not in translated.content, (
            "an empty tools map would grant no tools, where the source granted every tool"
        )

    def test_mode_is_subagent(self, tmp_path):
        agent = sync.read_agent(_agent_source(tmp_path, "scout"))

        translated = sync.translate_for_opencode(agent)

        assert sync.parse_document(translated.content).frontmatter["mode"] == "subagent", (
            "these definitions are spawned by another agent, never run as the session agent"
        )

    def test_description_survives_verbatim(self, tmp_path):
        agent = sync.read_agent(_agent_source(tmp_path, "scout"))

        translated = sync.translate_for_opencode(agent)

        assert (
            sync.parse_document(translated.content).frontmatter["description"]
            == "Use this agent to scout, and to report."
        ), "the description is what a router matches on, so it must carry across unchanged"

    def test_body_becomes_the_system_prompt_unchanged(self, tmp_path):
        agent = sync.read_agent(_agent_source(tmp_path, "scout", model="haiku"))

        translated = sync.translate_for_opencode(agent)

        assert sync.parse_document(translated.content).body == AGENT_BODY, (
            "the body is the system prompt and no rewrite applies to it"
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

        assert sync.resolve_skill_paths(installed, settings) == [str(install / "skills")], (
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

        assert sync.resolve_skill_paths(installed, settings) == [], (
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

        assert sync.resolve_skill_paths(installed, settings) == [], (
            "a disabled plugin's skills stay out, or the other agents load what Claude does not"
        )

    def test_enabled_plugin_missing_from_the_install_record_is_skipped(self, tmp_path):
        installed, settings = self._tree(tmp_path, {"ghost@nowhere": True}, {})

        assert sync.resolve_skill_paths(installed, settings) == [], (
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

        assert sync.resolve_skill_paths(installed, settings) == [str(new / "skills")], (
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

        assert sync.resolve_skill_paths(installed, settings) == [str(install / "skills")], (
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

        resolved = sync.resolve_skill_paths(installed, settings)

        assert resolved == sorted(resolved), (
            "the order must not follow the JSON key order, or the output churns between runs"
        )


class TestTranslateForPi:
    def test_model_stays_a_bare_tier_name(self, tmp_path):
        agent = sync.read_agent(_agent_source(tmp_path, "scout", model="haiku"))

        translated = sync.translate_for_pi(agent)

        assert sync.parse_document(translated.content).frontmatter["model"] == "haiku", (
            "pi resolves a tier name through its own model catalog"
        )

    def test_absent_model_emits_no_model_key(self, tmp_path):
        agent = sync.read_agent(_agent_source(tmp_path, "orchestrator"))

        translated = sync.translate_for_pi(agent)

        assert "model:" not in translated.content, (
            "emitting a model key where the source names none would pin an agent "
            "that should inherit"
        )

    def test_tools_render_comma_separated(self, tmp_path):
        agent = sync.read_agent(_agent_source(tmp_path, "scout", tools="Read, Grep, Bash"))

        translated = sync.translate_for_pi(agent)

        assert sync.parse_document(translated.content).frontmatter["tools"] == "read, grep, bash", (
            "pi reads tools as one comma-separated string, not as a map"
        )

    def test_glob_maps_to_find(self, tmp_path):
        agent = sync.read_agent(_agent_source(tmp_path, "scout", tools="Glob"))

        translated = sync.translate_for_pi(agent)

        assert sync.parse_document(translated.content).frontmatter["tools"] == "find", (
            "pi's find takes a glob pattern, which is what Claude's Glob does"
        )

    def test_tools_pi_lacks_drop_and_are_reported(self, tmp_path):
        agent = sync.read_agent(
            _agent_source(tmp_path, "skill-designer", tools="Read, Agent, ToolSearch")
        )

        translated = sync.translate_for_pi(agent)

        assert sync.parse_document(translated.content).frontmatter["tools"] == "read", (
            "pi carries bash, read, edit, write, grep, find, and ls, and nothing else"
        )
        assert translated.dropped == ("Agent", "ToolSearch"), (
            "a dropped tool narrows the agent's reach, so the run must name what it dropped"
        )

    def test_absent_tools_emits_no_tools_key(self, tmp_path):
        agent = sync.read_agent(_agent_source(tmp_path, "orchestrator"))

        translated = sync.translate_for_pi(agent)

        assert "tools:" not in translated.content, (
            "an empty tools list would grant no tools, where the source granted every tool"
        )

    def test_skills_are_inherited(self, tmp_path):
        agent = sync.read_agent(_agent_source(tmp_path, "scout"))

        translated = sync.translate_for_pi(agent)

        assert sync.parse_document(translated.content).frontmatter["inheritSkills"] is True, (
            "a subagent that cannot reach the skills its prompt names stalls on them"
        )

    def test_body_becomes_the_system_prompt_unchanged(self, tmp_path):
        agent = sync.read_agent(_agent_source(tmp_path, "scout", model="sonnet"))

        translated = sync.translate_for_pi(agent)

        assert sync.parse_document(translated.content).body == AGENT_BODY, (
            "the body is the system prompt and no rewrite applies to it"
        )


@pytest.fixture
def targets(tmp_path):
    """A complete source tree plus empty pi and opencode roots."""

    claude_home = tmp_path / "claude"
    _write(claude_home / "CLAUDE.md", "# Preamble\n\nStance.\n")
    _write(claude_home / "rules" / "alpha.sudolang.md", "Alpha {\n}\n")
    _write(
        claude_home / "rules" / "gated.sudolang.md",
        '---\npaths:\n  - "**/*.sh"\n---\n\nGated {\n}\n',
    )
    _agent_source(claude_home / "agents", "scout", model="haiku", tools="Read, Glob, Agent")
    _agent_source(claude_home / "agents", "orchestrator")

    plugin = tmp_path / "cache" / "software"
    (plugin / "skills").mkdir(parents=True)
    _write(
        claude_home / "plugins" / "installed_plugins.json",
        json.dumps({"plugins": {"software@seed": [{"scope": "user", "installPath": str(plugin)}]}}),
    )
    _write(claude_home / "settings.json", json.dumps({"enabledPlugins": {"software@seed": True}}))

    return sync.Targets(
        claude_home=claude_home,
        pi_home=tmp_path / "pi" / "agent",
        opencode_home=tmp_path / "config" / "opencode",
    )


class TestBuildPlan:
    def test_pi_agents_markdown_carries_the_preamble_and_the_unconditional_rules(self, targets):
        plan = sync.build_plan(targets)
        by_path = {f.path: f.content for f in plan.files}
        written = by_path[targets.pi_home / "AGENTS.md"]

        assert "Stance." in written, "pi reads the CLAUDE.md preamble from its context file"
        assert "Alpha {" in written, (
            "pi offers no second mechanism for rule files, so the rules travel in its context file"
        )
        assert "Gated {" not in written, (
            "a path-scoped rule reaches pi through the extension when a matching file is in play, "
            "so carrying it here would load it in every session and twice in a matching one"
        )

    def test_opencode_agents_markdown_carries_the_preamble_alone(self, targets):
        plan = sync.build_plan(targets)
        by_path = {f.path: f.content for f in plan.files}
        written = by_path[targets.opencode_home / "AGENTS.md"]

        assert "Stance." in written, "opencode reads the CLAUDE.md preamble from its context file"
        assert "Alpha {" not in written, (
            "opencode reads the rules through `instructions`, so repeating them here would double them"
        )

    def test_opencode_instructions_list_the_unconditional_rules(self, targets):
        plan = sync.build_plan(targets)
        owned = {(key.path, key.key): key.value for key in plan.keys}
        listed = owned[(targets.opencode_config, "instructions")]

        assert any(entry.endswith("alpha.sudolang.md") for entry in listed), (
            "every rule that loads each session must reach opencode"
        )

    def test_opencode_instructions_exclude_a_path_scoped_rule(self, targets):
        plan = sync.build_plan(targets)
        owned = {(key.path, key.key): key.value for key in plan.keys}
        listed = owned[(targets.opencode_config, "instructions")]

        assert not any(entry.endswith("gated.sudolang.md") for entry in listed), (
            "the plugin appends a path-scoped rule when a matching file is in play, so listing it "
            "here would load it in every session and twice in a matching one"
        )

    def test_build_plan_writes_no_copy_of_a_path_scoped_rule(self, targets):
        plan = sync.build_plan(targets)

        assert not any(f.path.name == "gated.sudolang.md" for f in plan.files), (
            "the plugin reads a path-scoped rule from its canonical file and strips the "
            "frontmatter itself, so no copy exists to fall out of date"
        )

    def test_every_source_agent_yields_one_file_per_target(self, targets):
        plan = sync.build_plan(targets)
        paths = {f.path for f in plan.files}

        assert {
            targets.opencode_home / "agents" / "scout.md",
            targets.opencode_home / "agents" / "orchestrator.md",
            targets.pi_home / "agents" / "scout.md",
            targets.pi_home / "agents" / "orchestrator.md",
        } <= paths, "each source agent must reach both targets"

    def test_skill_paths_render_as_a_paths_object(self, targets):
        plan = sync.build_plan(targets)
        by_path = {f.path: f.content for f in plan.files}
        written = json.loads(by_path[targets.skill_paths_file])

        assert list(written) == ["paths"], (
            "the consumer merging these reads a single paths key and nothing else"
        )

    def test_dropped_tools_are_reported_per_agent_and_target(self, targets):
        plan = sync.build_plan(targets)

        assert plan.dropped == (("pi", "scout", "Agent"),), (
            "pi carries no subagent tool, so scout's Agent grant cannot cross and must be named; "
            "opencode's task covers it, so nothing drops there"
        )


class TestApply:
    def test_first_run_creates_missing_parent_directories(self, targets):
        assert not targets.pi_home.exists(), "the fixture starts with no pi root"

        sync.main([], targets=targets)

        assert (targets.pi_home / "agents" / "scout.md").is_file(), (
            "a target directory that does not exist yet must be created rather than skipped"
        )

    def test_first_run_reports_each_file_it_created(self, targets, capsys):
        sync.main([], targets=targets)
        printed = capsys.readouterr().out

        assert str(targets.opencode_home / "AGENTS.md") in printed, (
            "a run that writes a file must name that file"
        )
        assert "created" in printed, "a file that did not exist reports as created, not updated"

    def test_second_run_reports_no_change(self, targets, capsys):
        sync.main([], targets=targets)
        capsys.readouterr()

        sync.main([], targets=targets)
        printed = capsys.readouterr().out

        assert "created" not in printed and "updated" not in printed, (
            "generating twice from unchanged sources must be a no-op, or the output is not "
            "a function of the sources alone"
        )

    def test_check_exits_zero_when_every_output_matches(self, targets):
        sync.main([], targets=targets)

        assert sync.main(["--check"], targets=targets) == 0, (
            "a tree the generator just wrote is by definition up to date"
        )

    def test_check_exits_nonzero_after_a_source_changes(self, targets):
        sync.main([], targets=targets)
        _write(targets.claude_home / "rules" / "alpha.sudolang.md", "Alpha {\n  changed\n}\n")

        assert sync.main(["--check"], targets=targets) != 0, (
            "an edited rule that never reached the generated files is what the push gate catches"
        )

    def test_check_exits_nonzero_when_an_output_is_missing(self, targets):
        assert sync.main(["--check"], targets=targets) != 0, (
            "a generated file that was never written differs from what a run would produce"
        )

    def test_check_writes_nothing(self, targets):
        sync.main(["--check"], targets=targets)

        assert not targets.pi_home.exists(), (
            "--check must be safe to run against a tree nobody intends to modify"
        )

    def test_check_leaves_a_stale_file_stale(self, targets):
        sync.main([], targets=targets)
        stale = targets.pi_home / "AGENTS.md"
        _write(stale, "hand-edited\n")

        sync.main(["--check"], targets=targets)

        assert stale.read_text(encoding="utf-8") == "hand-edited\n", (
            "--check reports a difference without repairing it"
        )
