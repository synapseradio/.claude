#!/usr/bin/env python3
"""One part of one delivery: `deliver.py --part K` reads a hook payload on stdin and prints the hook output.

`deliver.py --end` reads a session-end payload and ends the session's state.
"""

import argparse
import json
import os
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "lib"))

from rulesets import ordering
from rulesets.delivery.first_part import deliver_first
from rulesets.delivery.hook_output import hook_output
from rulesets.delivery.later_part import deliver_later
from rulesets.delivery.request import SessionEnd, SessionStart, Unreadable, parse_request
from rulesets.locations import Locations
from rulesets.session.lifecycle import on_session_end, on_session_start


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    which = parser.add_mutually_exclusive_group(required=True)
    which.add_argument("--part", type=int)
    which.add_argument("--end", action="store_true")
    arguments = parser.parse_args()
    raw = sys.stdin.read()
    locations = Locations.from_environment(os.environ)
    try:
        request = parse_request(json.loads(raw))
    except json.JSONDecodeError:
        request = Unreadable("the payload is not JSON")
    if isinstance(request, Unreadable):
        return 0
    if arguments.end:
        if isinstance(request, SessionEnd):
            on_session_end(request, locations)
        return 0
    if isinstance(request, SessionEnd):
        return 0
    part = arguments.part
    slot = ordering.slot_dir(locations.state, raw)
    ordering.register(slot, part)
    if part == 1:
        if isinstance(request, SessionStart):
            on_session_start(request, locations)
        output = deliver_first(request, locations, os.environ, slot)
    else:
        output = deliver_later(slot, part)
    sys.stdout.write(hook_output(request.event, output))
    return 0


if __name__ == "__main__":
    sys.exit(main())
