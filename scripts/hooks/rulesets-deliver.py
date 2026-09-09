#!/usr/bin/env python3.14
"""Deliver a session's or a delegate's ruleset into its context.

Wired to `SessionStart`, `SubagentStart`, and `PostModelSwitch` to deliver,
and to `PreToolUse` on `Agent` to record the per-spawn model a later
`SubagentStart` reads. Nothing under `rulesets/` auto-loads, so a failure
here would leave the session with no user rules; the resolver answers the
`default` tier wherever a tier, a manifest, or a body is unavailable, and
this shim swallows any error so the session still starts.
"""

import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from rulesets import resolve


def main() -> int:
    try:
        payload = json.loads(sys.stdin.read() or "{}")
    except json.JSONDecodeError:
        return 0
    if not isinstance(payload, dict):
        return 0

    try:
        output = resolve.deliver_payload(payload)
    except Exception:
        return 0

    if output:
        print(json.dumps(output))
    return 0


if __name__ == "__main__":
    sys.exit(main())
