#!/usr/bin/env python3
"""Record what the harness loaded into a session's context.

Wired to `InstructionsLoaded` with no matcher, so every load reason gets
a record. The event carries no decision control, so this hook cannot
block or alter a load, and it exits zero whatever happens to the write.

The hook command passes no flag, so the state directory resolves the way
every other entry point resolves it. `--state` names it outright, which the
forwarder at the old command path uses during the migration and a test uses
to keep off live state.
"""

import argparse
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "lib"))

from rulesets import audit, resolve


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state", default=None, help="the state directory to write")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    try:
        payload = json.loads(sys.stdin.read() or "{}")
    except json.JSONDecodeError:
        return 0
    if not isinstance(payload, dict):
        return 0

    state = args.state if args.state else resolve.state_dir()
    audit.append_record(
        audit.load_record(payload),
        session_id=payload.get("session_id") or "session",
        agent_id=payload.get("agent_id"),
        state=state,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
