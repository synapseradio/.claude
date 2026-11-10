#!/usr/bin/env python3
"""Report what a session and its delegates received, or how two sessions' deliveries differ.

Usage:
  session_report.py show --session ID [--root DIR]
  session_report.py compare A B

`show` prints three sections, each under its heading: `deliveries` (one line per delivery),
`delivery-check` (each difference from what composes now), and `load-check` (each loaded file
named for a rule of the pool). It exits 1 where either check printed a line.

`compare` prints each session's flags, then each scope whose rules differ: the session, and
each delegate, matched by agent type in the order the delegates started. Under a scope, a line
names a rule and the variant each session received, `default` for the default form and
`absent` where the session received no such rule.
"""

import argparse
import os
import pathlib
import sys
from collections import Counter

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "lib"))

from rulesets.audit import log
from rulesets.audit.counted import counted
from rulesets.audit.deliveries import deliveries
from rulesets.audit.delivery_check import delivery_check
from rulesets.audit.delivery_record import AgentLine, DeliveryRecord
from rulesets.audit.load_check import load_check
from rulesets.locations import Locations

_NONE = "-"
_SESSION = "session"

type Received = dict[str, str | None]


def show(locations: Locations, session: str, root: pathlib.Path) -> int:
    differences = [difference.line() for difference in delivery_check(locations, session, root)]
    loads = [finding.line() for finding in load_check(locations, session, root)]
    sections = (
        ("deliveries", [context.line() for context in deliveries(locations, session)]),
        ("delivery-check", differences),
        ("load-check", loads),
    )
    print("\n\n".join("\n".join([heading, *lines]) for heading, lines in sections))
    return 1 if differences or loads else 0


def _records(locations: Locations, session: str) -> tuple[DeliveryRecord, ...]:
    path = log.session_dir(locations, session) / log.DELIVERIES_FILE
    return counted(log.read_as(path, DeliveryRecord.from_json))


def scopes(records: tuple[DeliveryRecord, ...]) -> dict[str, DeliveryRecord]:
    """The latest record of each scope: the session, and each delegate as `delegate <type> #<n>`."""

    found: dict[str, DeliveryRecord] = {}
    names: dict[str, str] = {}
    started: Counter[str] = Counter()
    for record in records:
        if record.kind == _SESSION:
            found[_SESSION] = record
            continue
        delegate = record.agent_id or _NONE
        if delegate not in names:
            agent = record.agent.name if isinstance(record.agent, AgentLine) else _NONE
            started[agent] += 1
            names[delegate] = f"delegate {agent} #{started[agent]}"
        found[names[delegate]] = record
    return found


def _received(record: DeliveryRecord) -> Received:
    return {line.rule: line.variant for line in record.rules}


def _flags(found: dict[str, DeliveryRecord]) -> str:
    record = found.get(_SESSION)
    names = [flag.name for flag in record.flags] if record else []
    return ",".join(names) or _NONE


def _shown(received: Received, rule: str) -> str:
    if rule not in received:
        return "absent"
    return received[rule] or "default"


def compare(locations: Locations, first: str, second: str) -> int:
    left = scopes(_records(locations, first))
    right = scopes(_records(locations, second))
    print(f"flags {first}: {_flags(left)}")
    print(f"flags {second}: {_flags(right)}")
    for scope in [*left, *(name for name in right if name not in left)]:
        if scope not in right or scope not in left:
            print(f"{scope}\n  only in {first if scope in left else second}")
            continue
        one, other = _received(left[scope]), _received(right[scope])
        lines = [
            f"  {rule}  {first}: {_shown(one, rule)}  {second}: {_shown(other, rule)}"
            for rule in sorted(one.keys() | other.keys())
            if one.get(rule, _NONE) != other.get(rule, _NONE)
        ]
        if lines:
            print("\n".join([scope, *lines]))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="session_report.py", description=__doc__.splitlines()[0])
    commands = parser.add_subparsers(dest="command", required=True)
    showing = commands.add_parser("show", help="what one session received, and both checks")
    showing.add_argument("--session", required=True, help="the session identifier")
    showing.add_argument("--root", type=pathlib.Path, help="the rulesets directory")
    comparing = commands.add_parser("compare", help="how two sessions' deliveries differ")
    comparing.add_argument("first", help="the first session identifier")
    comparing.add_argument("second", help="the second session identifier")
    arguments = parser.parse_args(argv)
    locations = Locations.from_environment(os.environ)
    if arguments.command == "show":
        return show(locations, arguments.session, arguments.root or locations.rulesets)
    return compare(locations, arguments.first, arguments.second)


if __name__ == "__main__":
    sys.exit(main())
