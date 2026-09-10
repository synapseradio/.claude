#!/usr/bin/env python3.14
"""Forward to the epistemic-marks plugin's verification hook.

The live `settings.json` is untracked, so a checkout that moved this file's
code reaches a running session before anyone rewrites the three commands that
name it. A Stop, SubagentStop, or PostToolBatch command resolving to nothing
is not an error the harness reports: the turn simply closes, so every reply
would ship with its marks unverified and nothing would say so. This file keeps
the old command path executable and hands stdin, stdout, and its arguments to
the plugin's hook.

It forwards through the plugin's own `with-python.sh`, which is the exact
invocation the plugin's `hooks.json` uses, so the interpreter this hook runs
under is chosen in one place rather than two.

A target that is not there is answered the way the target answers a mark it
cannot resolve: a `systemMessage`, which reaches the user without blocking the
turn. Blocking a Stop on a missing plugin would trap the session in a loop.

It is deleted once the live `settings.json` names the plugin's own hooks and
one session has verified a reply through them.
"""

import json
import os
import pathlib
import sys

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
PLUGIN_HOOKS = REPO_ROOT / "features" / "epistemic-marks" / "hooks"


def announce_missing(target: pathlib.Path) -> int:
    """Say, in the session's own transcript, that the plugin's hook is not there."""

    notice = (
        "Epistemic marks went unverified: the hook this session's settings file "
        f"forwards to is not in this checkout ({target}). Every mark in the reply "
        "above is unchecked. Install the epistemic-marks plugin and point the "
        "settings file's Stop, SubagentStop, and PostToolBatch hooks at it."
    )
    json.dump({"systemMessage": notice}, sys.stdout)
    return 0


def main(argv: list[str]) -> int:
    target = PLUGIN_HOOKS / "verify-marks.py"
    runner = PLUGIN_HOOKS / "with-python.sh"
    if not target.is_file() or not runner.is_file():
        return announce_missing(target)
    os.execv("/bin/bash", ["bash", str(runner), str(target), *argv])


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
