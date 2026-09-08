#!/usr/bin/env python3
"""Tests for `scripts/agent-configs/translate-for-opencode.py`.

Run with `python3.14 -m pytest scripts/tests/test_translate_for_opencode.py`.

Every test builds its own tree under a tmp_path and passes a Targets naming
it, so no test reads or writes this checkout's own configuration or pi's or
opencode's real directories.
"""

import importlib.util
import json
import pathlib
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


opencode = _load("translate_for_opencode_test", "translate-for-opencode.py")
pi = _load("translate_for_pi_test_via_opencode", "translate-for-pi.py")
render = _load("render_working_rules_test_via_opencode", "render-working-rules.py")


def _write(path: pathlib.Path, text: str) -> pathlib.Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


PREAMBLE = '<hello from="user">\n~\n/~\n</hello>\n\n<stance>\n\nPlay.\n\n</stance>'


def _element(name: str, body: str) -> str:
    return f'<rule name="{name}">\n\n{body}\n\n</rule>'


ALPHA = _element("alpha", "Alpha holds.")


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
    _write(claude_home / "rules" / "alpha.md", f"{ALPHA}\n")
    _write(claude_home / "agents" / "scout.md", _agent_source(model=model))
    _write(claude_home / "plugins" / "installed_plugins.json", json.dumps({"plugins": {}}))
    _write(claude_home / "settings.json", json.dumps({"enabledPlugins": {}}))
    return projection.Targets(
        claude_home=claude_home,
        pi_home=tmp_path / "pi",
        opencode_home=tmp_path / "opencode",
        working_rules_order=("alpha",),
    )


class TestTranslateForOpencode:
    def test_carries_the_mapped_model_id(self, tmp_path):
        agent = projection.read_agent(_write(tmp_path / "scout.md", _agent_source(model="haiku")))

        translated = opencode.translate_for_opencode(agent)

        frontmatter = projection.parse_document(translated.content).frontmatter
        assert frontmatter["model"] == opencode.OPENCODE_MODEL_IDS["haiku"], (
            "opencode reads a fully qualified model id, not the short name Claude Code carries"
        )

    def test_carries_the_subagent_mode(self, tmp_path):
        agent = projection.read_agent(_write(tmp_path / "scout.md", _agent_source()))

        translated = opencode.translate_for_opencode(agent)

        assert projection.parse_document(translated.content).frontmatter["mode"] == "subagent", (
            "every translated agent runs as an opencode subagent"
        )


class TestBuildPreamble:
    def test_carries_the_claude_md_body_alone(self, tmp_path):
        targets = _targets(tmp_path)

        built = opencode.build_preamble(targets.claude_md)

        assert "Play." in built and "Alpha holds." not in built, (
            "opencode reads the always-on rules through the instructions key it owns separately, "
            "so repeating them in AGENTS.md would load them twice"
        )


class TestOneJobFails:
    """`config-projection` requirement: each projection job runs independently.

    Scenario: One job fails (the opencode translation job fails, and the
    working-rules render and pi's outputs are unaffected by that failure).
    """

    def test_opencode_failure_leaves_the_render_and_pi_outputs_intact(self, tmp_path):
        targets = _targets(tmp_path, model="an-unmapped-model")

        assert render.main([], targets=targets) == 0
        assert pi.main([], targets=targets) == 0
        render_before = targets.working_rules.read_text(encoding="utf-8")
        pi_agents_before = (targets.pi_home / "agents" / "scout.md").read_text(encoding="utf-8")

        with pytest.raises(KeyError, match="an-unmapped-model"):
            opencode.main([], targets=targets)

        assert not (targets.opencode_home / "agents" / "scout.md").exists(), (
            "a job that fails while building its plan must write none of its own outputs"
        )
        assert targets.working_rules.read_text(encoding="utf-8") == render_before, (
            "the opencode job's failure must leave the working-rules render untouched"
        )
        assert (targets.pi_home / "agents" / "scout.md").read_text(
            encoding="utf-8"
        ) == pi_agents_before, "the opencode job's failure must leave pi's outputs untouched"
