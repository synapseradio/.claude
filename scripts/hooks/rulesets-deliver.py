#!/usr/bin/env python3.14
"""Forward to the model-scoped-rulesets plugin's delivery hook.

The live `settings.json` is untracked, so a checkout that moved this file's
code reaches a running session before the alignment sweep rewrites the
command that names it. Nothing in the corpus auto-loads, so during that
window a command resolving to nothing would leave every session with no user
rules. This file keeps the old command path executable and hands stdin and
stdout to the new shim, naming the moved corpus and the state directory the
old code wrote to.

A target that is not there is the hazard this file exists for, met one step
later, so it is answered the way the target answers its own failures: context
naming the failure and exit 0, never a session that starts quietly with no
rules.

It is deleted once the live `settings.json` names the plugin's own hooks and
one session has verified delivery through them.
"""

import json
import os
import pathlib
import sys

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
PLUGIN_ROOT = REPO_ROOT / "features" / "model-scoped-rulesets"


def config_root() -> pathlib.Path:
    override = os.environ.get("CLAUDE_CONFIG_DIR")
    if override:
        return pathlib.Path(override)
    return pathlib.Path.home() / ".claude"


def announce_missing(target: pathlib.Path) -> int:
    """Say, in the session's context, that the plugin's hook is not there."""

    try:
        payload = json.loads(sys.stdin.read() or "{}")
    except json.JSONDecodeError:
        payload = {}
    event = payload.get("hook_event_name") if isinstance(payload, dict) else None
    text = "\n".join(
        [
            f"<!-- ruleset: delivery failed, from {pathlib.Path(__file__).name}, 0 stems -->",
            f"<!-- note: the hook this command forwards to is not there: {target} -->",
            "",
            "Ruleset delivery failed, so this session is running without its user rules. "
            "Tell the user this before doing anything else.",
            "",
            "The live settings file still names this forwarder, and the plugin hook it "
            "forwards to is missing from this checkout. Install the plugin and point the "
            "settings file's hooks at it, then start a new session.",
        ]
    )
    output = {
        "hookSpecificOutput": {
            "hookEventName": event or "SessionStart",
            "additionalContext": text,
        }
    }
    print(json.dumps(output))
    return 0


def main() -> int:
    target = PLUGIN_ROOT / "hooks" / "deliver.py"
    if not target.is_file():
        return announce_missing(target)
    os.execv(
        sys.executable,
        [
            sys.executable,
            str(target),
            "--root",
            str(REPO_ROOT / "rulesets"),
            "--state",
            str(config_root() / ".tmp" / "rulesets"),
        ],
    )


if __name__ == "__main__":
    sys.exit(main())
