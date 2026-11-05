#!/usr/bin/env python3
"""One part of one delivery: `deliver.py --part K` reads a hook payload on stdin and prints the hook output.

`deliver.py --end` reads a session-end payload and ends the session's state. Every run exits 0.
"""

import argparse
import json
import os
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "lib"))

from rulesets import ordering
from rulesets.delivery.failure import run_guarded
from rulesets.delivery.first_part import deliver_first
from rulesets.delivery.hook_output import hook_output
from rulesets.delivery.later_part import deliver_later
from rulesets.delivery.request import (
    HookRequest,
    SessionEnd,
    SessionStart,
    Unreadable,
    parse_request,
)
from rulesets.locations import Locations
from rulesets.session.lifecycle import on_session_end, on_session_start


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    which = parser.add_mutually_exclusive_group(required=True)
    which.add_argument("--part", type=int)
    which.add_argument("--end", action="store_true")
    arguments = parser.parse_args()
    raw = sys.stdin.read()
    try:
        request = parse_request(json.loads(raw))
    except json.JSONDecodeError:
        request = Unreadable("the payload is not JSON")
    if isinstance(request, Unreadable):
        return 0
    locations = Locations.from_environment(os.environ)
    hooks = pathlib.Path(__file__).resolve().parent
    part = 0 if arguments.end else arguments.part
    flag = "--end" if arguments.end else f"--part {part}"
    command = f'bash "{hooks}/with-python.sh" "{hooks}/deliver.py" {flag} < payload.json'
    output = run_guarded(
        lambda: _output(request, arguments.end, part, raw, locations),
        event=request.event,
        session_id=request.session_id,
        first_part=part == 1,
        command=command,
        locations=locations,
    )
    sys.stdout.write(output)
    return 0


def _output(request: HookRequest, ending: bool, part: int, raw: str, locations: Locations) -> str:
    """The hook output of one run, or an empty string where the run has nothing to say."""

    if ending:
        if isinstance(request, SessionEnd):
            on_session_end(request, locations)
        return ""
    if isinstance(request, SessionEnd):
        return ""
    slot = ordering.slot_dir(locations.state, raw)
    ordering.register(slot, part)
    if part == 1:
        lifecycle_notices = (
            on_session_start(request, locations) if isinstance(request, SessionStart) else ()
        )
        return hook_output(
            request.event,
            deliver_first(request, locations, os.environ, slot, lifecycle_notices),
        )
    return hook_output(request.event, deliver_later(slot, part))


if __name__ == "__main__":
    sys.exit(main())
