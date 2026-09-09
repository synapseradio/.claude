"""The delivery shim swallows every error and never fails the session.

Nothing under `rulesets/` auto-loads, so a shim that raised would leave a
session with no user rules. These tests run the shim as the harness does,
as a subprocess reading a payload on stdin, against a temporary config and
state directory so no live rule or record is touched.
"""

import json
import pathlib
import subprocess
import sys

import yaml

HOOK = pathlib.Path(__file__).resolve().parent / "rulesets-deliver.py"

MODELS = {
    "opus": ["opus", "claude-opus"],
    "sonnet": ["sonnet", "claude-sonnet"],
    "haiku": ["haiku", "claude-haiku"],
    "fable": ["fable", "claude-fable"],
}

TIERS = ("default", "fable", "opus", "sonnet", "haiku")


def build_config(tmp_path):
    """A config directory whose `rulesets/` holds a manifest, models, bodies."""

    root = tmp_path / "rulesets"
    for tier in TIERS:
        (root / tier).mkdir(parents=True, exist_ok=True)
    for stem in ("alpha", "beta"):
        (root / "default" / f"{stem}.md").write_text(f"Body {stem}.\n", encoding="utf-8")
    manifest = {"tiers": {tier: {"include": "*"} for tier in TIERS}}
    (root / "manifest.yaml").write_text(yaml.safe_dump(manifest), encoding="utf-8")
    (root / "models.yaml").write_text(yaml.safe_dump(MODELS), encoding="utf-8")
    return tmp_path


def run(payload, config, state):
    env = {
        "CLAUDE_CONFIG_DIR": str(config),
        "RULESETS_STATE_DIR": str(state),
        "PATH": "/usr/bin:/bin",
    }
    stdin = payload if isinstance(payload, str) else json.dumps(payload)
    return subprocess.run(
        [sys.executable, str(HOOK)],
        input=stdin,
        capture_output=True,
        text=True,
        env=env,
    )


class TestDeliveryShim:
    def test_a_session_start_delivers_the_tier_and_exits_zero(self, tmp_path):
        config = build_config(tmp_path)
        state = tmp_path / "state"
        payload = {
            "hook_event_name": "SessionStart",
            "session_id": "s1",
            "model": "claude-haiku-4-5",
        }

        result = run(payload, config, state)

        assert result.returncode == 0
        emitted = json.loads(result.stdout)
        text = emitted["hookSpecificOutput"]["additionalContext"]
        assert "tier haiku" in text

    def test_malformed_stdin_exits_zero_with_no_output(self, tmp_path):
        config = build_config(tmp_path)

        result = run("not json at all", config, tmp_path / "state")

        assert result.returncode == 0
        assert result.stdout.strip() == ""

    def test_a_non_object_payload_exits_zero_with_no_output(self, tmp_path):
        config = build_config(tmp_path)

        result = run("[1, 2, 3]", config, tmp_path / "state")

        assert result.returncode == 0
        assert result.stdout.strip() == ""

    def test_a_broken_config_still_exits_zero(self, tmp_path):
        # No `rulesets/` under the config, so the resolver finds no manifest;
        # the shim swallows the error and the session still starts.
        payload = {
            "hook_event_name": "SessionStart",
            "session_id": "s1",
            "model": "claude-haiku-4-5",
        }

        result = run(payload, tmp_path / "empty", tmp_path / "state")

        assert result.returncode == 0
