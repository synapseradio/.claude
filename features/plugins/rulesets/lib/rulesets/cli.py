#!/usr/bin/env python3
"""Command line for the rulesets engine: `check --root <dir>` and `toggle --session <id> <action>`.

This module parses arguments, prints, and sets the exit status. Every finding comes from
`rulesets.check.run`, and every line's wording from `rulesets.check.report_format`. A toggle's
change comes from `rulesets.session.toggle`.
"""

import argparse
import os
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from rulesets.check.report_format import report_lines
from rulesets.check.run import check
from rulesets.locations import Locations
from rulesets.session.state import Band, SessionState, read_state, remove_state, write_state
from rulesets.session.toggle import (
    Clear,
    SetBand,
    SetFlag,
    ToggleAction,
    UndeclaredFlag,
    UnsetFlag,
    apply_toggle,
)
from rulesets.source.directory import Present, read_directory

_USAGE_ERROR = 2

# What each toggle action does to the delegates started afterwards, as a clause after
# "Delegates started from now on".
_EFFECTS = {
    "all": "receive every rule in the pool",
    "none": "receive no rule",
    "flag": "hold the flag {name}",
    "unflag": "do not hold the flag {name}",
    "clear": "compose from the manifest and the launch flags alone",
}


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="cli.py", description=__doc__.splitlines()[0])
    commands = parser.add_subparsers(dest="command", required=True)
    checking = commands.add_parser(
        "check",
        help="print every error and warning of a rulesets directory; exit 1 only on an error",
    )
    checking.add_argument("--root", required=True, type=pathlib.Path, help="the rulesets directory")
    toggling = commands.add_parser(
        "toggle", help="change what the delegates this session starts from now on receive"
    )
    toggling.add_argument("--session", required=True, help="the session whose state changes")
    toggling.add_argument("action", choices=list(_EFFECTS), help="what the toggle does")
    toggling.add_argument("name", nargs="?", help="the flag, for the actions flag and unflag")
    return parser


def _action(action: str, name: str | None) -> ToggleAction | None:
    """The toggle action the words name, or None where a flag name is missing or surplus."""

    match action, name:
        case "all", None:
            return SetBand(Band.ALL)
        case "none", None:
            return SetBand(Band.NONE)
        case "clear", None:
            return Clear()
        case "flag", str():
            return SetFlag(name)
        case "unflag", str():
            return UnsetFlag(name)
        case _:
            return None


def _toggle(session: str, action: ToggleAction) -> int:
    locations = Locations.from_environment(os.environ)
    match read_directory(locations.rulesets).manifest:
        case Present(manifest):
            declared = manifest.flags
        case _:
            declared = ()
    match apply_toggle(declared, read_state(locations, session), action):
        case UndeclaredFlag(name):
            print(f"cli.py: the manifest declares no flag `{name}`", file=sys.stderr)
            return 1
        case SessionState() as state if state == SessionState():
            remove_state(locations, session)
        case SessionState() as state:
            write_state(locations, session, state)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    arguments = parser.parse_args(argv)
    if arguments.command == "toggle":
        action = _action(arguments.action, arguments.name)
        if action is None:
            parser.error("a flag name goes with the actions flag and unflag, and with no other")
        status = _toggle(arguments.session, action)
        if status == 0:
            effect = _EFFECTS[arguments.action].format(name=arguments.name)
            print(f"Delegates started from now on {effect}.")
        return status
    if not arguments.root.is_dir():
        print(f"cli.py: no rulesets directory at {arguments.root}", file=sys.stderr)
        return _USAGE_ERROR
    report = check(arguments.root)
    for line in report_lines(report):
        print(line)
    return 1 if report.errors else 0


if __name__ == "__main__":
    sys.exit(main())
