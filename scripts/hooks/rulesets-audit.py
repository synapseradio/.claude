#!/usr/bin/env python3.14
"""Record what the harness loaded into a session's context.

Wired to `InstructionsLoaded` with no matcher, so every load reason gets
a record. The event carries no decision control, so this hook cannot
block or alter a load, and it exits zero whatever happens to the write.
"""

import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from rulesets import audit


def main() -> int:
    try:
        payload = json.loads(sys.stdin.read() or "{}")
    except json.JSONDecodeError:
        return 0
    if not isinstance(payload, dict):
        return 0

    audit.append_record(
        audit.load_record(payload),
        session_id=payload.get("session_id") or "session",
        agent_id=payload.get("agent_id"),
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
