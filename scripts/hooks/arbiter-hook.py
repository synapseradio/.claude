#!/usr/bin/env python3
"""Arbiter hook entry point. Library: scripts/arbiter/lib/.

Reads a Claude Code hook payload on stdin, hands it to
`arbiter.lib.dispatch`, which loads `bindings.yaml`, derives
`(event, tool)`, judges the body through the local llama-server, and
writes the hook-event-shaped JSON to stdout when one or more verdicts
fire.

The hook fails closed: if the llama-server is unreachable, returns an
unrecognized response, or times out, the static fallback message is
emitted and the binding's action fires. Set `BLOCK_PLAN_NO_JUDGE=1` to
skip the HTTP call and emit the same fallback — useful only when
diagnosing the server itself.

Master on-off switch: when the sentinel file at
`~/.claude/arbiter/state/disabled` exists, the hook exits 0 silently
before any dispatch. This bypasses the fails-closed contract on
purpose — the sentinel is an explicit operator decision, not a
transient outage.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "arbiter"))

from lib import dispatch

ARBITER_DISABLED_FILE = Path.home() / ".claude" / "arbiter" / "state" / "disabled"


def main() -> None:
    if ARBITER_DISABLED_FILE.exists():
        sys.exit(0)
    try:
        payload = json.load(sys.stdin)
    except ValueError:
        sys.exit(0)
    dispatch(payload, sys.stdout)
    sys.exit(0)


if __name__ == "__main__":
    main()
