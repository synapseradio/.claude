#!/usr/bin/env python3
"""A hook that moved into a plugin leaves a forwarder at the path it left.

The live `settings.json` is untracked and names seven scripts under
`scripts/hooks/`. A checkout that moved their code reaches a running session
before anyone rewrites those commands. The harness does not report a hook
command that resolves to nothing: the tool call proceeds, the turn closes, the
session starts. So the whole cost of a broken forwarder is paid silently, and
what it buys is a session running with its secret guards absent, its marks
unverified, or its rules unloaded.

Two properties hold that off. Every forwarder resolves to a target that is
actually there, and a forwarder whose target is gone still exits zero and says
so on the channel its own event gives it.

Run with `python3.14 -m pytest scripts/tests/test_forwarders.py`.
"""

import json
import os
import pathlib
import shutil
import subprocess
import sys

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
HOOKS = REPO_ROOT / "scripts" / "hooks"

# Each forwarder, the plugin hook it hands off to, and where it announces a
# handoff it could not make. "stdout" means a JSON object the harness reads;
# "state" means a JSONL line under the state directory, which is all an
# InstructionsLoaded hook gets — it carries no decision control.
FORWARDERS = [
    ("block-secret-leaks.sh", "bash-guards/hooks/block-secret-leaks.sh", "stdout"),
    ("block-secret-file-reads.sh", "bash-guards/hooks/block-secret-file-reads.sh", "stdout"),
    ("deny-inplace-stream-edit.sh", "bash-guards/hooks/deny-inplace-stream-edit.sh", "stdout"),
    ("ask-remote-data-send.sh", "bash-guards/hooks/ask-remote-data-send.sh", "stdout"),
    ("verify-marks.py", "epistemic-marks/hooks/verify-marks.py", "stdout"),
    ("rulesets-deliver.py", "model-scoped-rulesets/hooks/deliver.py", "stdout"),
    ("rulesets-audit.py", "model-scoped-rulesets/hooks/record-load.py", "state"),
]

IDS = [name for name, _, _ in FORWARDERS]


def run(script: pathlib.Path, config_root: pathlib.Path) -> subprocess.CompletedProcess:
    """Run a forwarder with an empty hook payload and no real config in reach."""

    argv = ["bash", str(script)] if script.suffix == ".sh" else [sys.executable, str(script)]
    return subprocess.run(
        argv,
        input=json.dumps({"session_id": "forwarder-test"}),
        capture_output=True,
        text=True,
        timeout=15,
        env={**os.environ, "CLAUDE_CONFIG_DIR": str(config_root)},
    )


@pytest.mark.parametrize(("forwarder", "target", "channel"), FORWARDERS, ids=IDS)
class TestForwarders:
    def test_the_forwarder_is_there_and_runnable(self, forwarder, target, channel):
        script = HOOKS / forwarder

        assert script.is_file(), (
            f"the live settings file names {script} and nothing is there, so the hook it "
            "stands in for does not run and the harness reports no error"
        )

    def test_the_forwarder_resolves_to_a_hook_that_exists(self, forwarder, target, channel):
        resolved = REPO_ROOT / "features" / target

        assert resolved.is_file(), (
            f"{forwarder} hands off to {resolved}, which is not there, so renaming a hook "
            "inside a plugin breaks the old path with nothing to say it did"
        )

    def test_a_missing_plugin_still_exits_zero_and_says_so(
        self, forwarder, target, channel, tmp_path
    ):
        """The gap this forwarder exists for, met one step later."""

        tree = tmp_path / "root"
        (tree / "scripts" / "hooks" / "lib").mkdir(parents=True)
        shutil.copy2(HOOKS / forwarder, tree / "scripts" / "hooks" / forwarder)
        if (HOOKS / "lib" / "forward-guard.sh").is_file():
            shutil.copy2(
                HOOKS / "lib" / "forward-guard.sh",
                tree / "scripts" / "hooks" / "lib" / "forward-guard.sh",
            )
        config_root = tmp_path / "config"
        config_root.mkdir()

        result = run(tree / "scripts" / "hooks" / forwarder, config_root)

        assert result.returncode == 0, (
            f"{forwarder} exited {result.returncode} with its target absent. A nonzero exit "
            f"from a PreToolUse hook is the harness's block code. stderr: {result.stderr}"
        )
        if channel == "stdout":
            assert result.stdout.strip(), (
                f"{forwarder} said nothing with its target absent, so the session runs "
                "without the check and no one is told"
            )
            assert isinstance(json.loads(result.stdout), dict), (
                f"{forwarder} wrote something the harness cannot read: {result.stdout!r}"
            )
        else:
            notes = list(config_root.rglob("*.jsonl"))
            assert notes, (
                f"{forwarder} left no record with its target absent, so the gap is "
                f"invisible in the trail it is supposed to write. stderr: {result.stderr}"
            )
