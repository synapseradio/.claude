#!/usr/bin/env python3
"""One part of one delivery: `deliver.py --part K` reads a hook payload on stdin and prints the hook output.

`deliver.py --part 1 --rerun` runs the first part apart from any delivery, as a failure notice's command does.
`deliver.py --end` reads a session-end payload and ends the session's state. Every run exits 0.
"""

import argparse
import contextlib
import json
import os
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "lib"))

from rulesets import ordering
from rulesets.delivery.failure import run_guarded
from rulesets.delivery.first_part import deliver_first
from rulesets.delivery.fork import deliver_fork
from rulesets.delivery.hook_output import PartOutput, hook_output
from rulesets.delivery.later_part import deliver_later
from rulesets.delivery.plan import Silent, new_generation, write_plan
from rulesets.delivery.replay import deliver_replay
from rulesets.delivery.request import (
    DeliveryStart,
    ForkStart,
    ModelSwitch,
    SessionEnd,
    SessionStart,
    SubagentStart,
    Unreadable,
    parse_request,
)
from rulesets.delivery.rerun import RERUN_FLAG
from rulesets.delivery.switch import deliver_switch
from rulesets.delivery.unreadable import report_unreadable
from rulesets.locations import Locations
from rulesets.session.lifecycle import on_session_end, on_session_start


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    which = parser.add_mutually_exclusive_group(required=True)
    which.add_argument("--part", type=int)
    which.add_argument("--end", action="store_true")
    parser.add_argument(
        RERUN_FLAG, action="store_true", help="run the first part apart from any delivery"
    )
    arguments = parser.parse_args()
    try:
        raw = sys.stdin.buffer.read().decode("utf-8")
        request = parse_request(json.loads(raw))
    except UnicodeDecodeError, json.JSONDecodeError:
        raw, request = "", Unreadable("the payload is not UTF-8 JSON")
    locations = Locations.from_environment(os.environ)
    if isinstance(request, Unreadable):
        if arguments.end or arguments.part == 1:
            sys.stdout.write(report_unreadable(request, locations))
        return 0
    hooks = pathlib.Path(__file__).resolve().parent
    part = 0 if arguments.end else arguments.part
    output = run_guarded(
        lambda: _output(request, arguments.end, part, arguments.rerun, raw, locations),
        request=request,
        first_part=part == 1,
        raw_payload=raw,
        hooks=hooks,
        locations=locations,
    )
    sys.stdout.write(output)
    return 0


def _output(
    request: DeliveryStart | SessionEnd,
    ending: bool,
    part: int,
    rerun: bool,
    raw: str,
    locations: Locations,
) -> str:
    """The hook output of one run, or an empty string where the run has nothing to say."""

    if ending:
        if isinstance(request, SessionEnd):
            on_session_end(request, locations)
        return ""
    if isinstance(request, SessionEnd):
        return ""
    slot = (
        ordering.private_slot_dir(locations.state)
        if rerun
        else ordering.slot_dir(locations.state, raw)
    )
    if part != 1:
        return hook_output(request.event, deliver_later(request, locations, slot, part))
    generation = new_generation()
    ordering.hold(slot, generation, 1)
    try:
        return hook_output(request.event, _first_part(request, locations, slot, generation))
    except Exception:
        with contextlib.suppress(OSError):
            write_plan(slot, Silent(generation))
        raise


def _first_part(
    request: DeliveryStart, locations: Locations, slot: pathlib.Path, generation: str
) -> PartOutput:
    match request:
        case ForkStart():
            return deliver_fork(request, locations, slot, generation)
        case ModelSwitch():
            return deliver_switch(request, locations, os.environ, slot, generation)
        case SessionStart():
            notices = on_session_start(request, locations)
            return deliver_first(request, locations, os.environ, slot, generation, notices)
        case SubagentStart():
            replayed = deliver_replay(request, locations, slot, generation)
            if replayed is not None:
                return replayed
            return deliver_first(request, locations, os.environ, slot, generation)


if __name__ == "__main__":
    sys.exit(main())
