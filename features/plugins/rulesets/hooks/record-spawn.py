#!/usr/bin/env python3
"""Record the model a caller names for one `Agent` spawn; print nothing and exit 0."""

import json
import os
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "lib"))

from rulesets import spawn_log
from rulesets.locations import Locations


def main() -> int:
    try:
        record(json.loads(sys.stdin.read()), Locations.from_environment(os.environ))
    except Exception:
        return 0
    return 0


def record(payload: object, locations: Locations) -> None:
    """Append the spawn's model, joined on the prompt and the agent type; skip a spawn naming none."""

    if not isinstance(payload, dict):
        return
    tool_input = payload.get("tool_input")
    session_id = payload.get("session_id")
    if not isinstance(tool_input, dict) or not isinstance(session_id, str) or not session_id:
        return
    model = tool_input.get("model")
    if model in (None, ""):
        return
    spawn_log.append_spawn(
        session_id,
        _text(payload.get("prompt_id")),
        _text(tool_input.get("subagent_type")),
        model,
        locations.state,
    )


def _text(value: object) -> str | None:
    return value if isinstance(value, str) and value else None


if __name__ == "__main__":
    sys.exit(main())
