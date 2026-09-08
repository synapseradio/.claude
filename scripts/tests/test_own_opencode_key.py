#!/usr/bin/env python3
"""Tests for `scripts/agent-configs/own-opencode-key.py`.

Run with `python3.14 -m pytest scripts/tests/test_own_opencode_key.py`.

Every test builds its own tree under a tmp_path and passes a Targets naming
it, so no test reads or writes the real `~/.config/opencode/opencode.json`.
"""

import importlib.util
import json
import pathlib
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
    _write(claude_home / "rules" / "alpha.md", f"{ALPHA}\n")
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
