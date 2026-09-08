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
import sys

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
    _write(claude_home / "rules" / "alpha.md", f"{ALPHA}\n")
    _write(claude_home / "agents" / "scout.md", AGENT_SOURCE)
    _write(claude_home / "plugins" / "installed_plugins.json", json.dumps({"plugins": {}}))
    _write(claude_home / "settings.json", json.dumps({"enabledPlugins": {}}))
    return projection.Targets(
        claude_home=claude_home,
        pi_home=tmp_path / "pi",
        opencode_home=tmp_path / "opencode",
        working_rules_order=("alpha",),
    )


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
