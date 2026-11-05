#!/usr/bin/env python3
"""Command line for the rulesets engine: `check`, `explain`, `eject`, `render`, `toggle`, `delivery-check`, `load-check`, and `deliveries`.

This module parses arguments, prints, and sets the exit status. Every finding comes from
`rulesets.check.run`, and every line's wording from `rulesets.check.report_format`. An explanation comes from `rulesets.explain`. A toggle's
change comes from `rulesets.session.toggle`, a delivery difference from
`rulesets.audit.delivery_check`, a still auto-loading file from `rulesets.audit.load_check`, a
delivery line from `rulesets.audit.deliveries`, ejected files from `rulesets.eject`, and a render
from `rulesets.render`.
"""

import argparse
import os
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from rulesets.audit.deliveries import deliveries
from rulesets.audit.delivery_check import delivery_check
from rulesets.audit.load_check import load_check
from rulesets.check.report_format import report_lines
from rulesets.check.run import check
from rulesets.compose.composition import compose
from rulesets.eject import eject
from rulesets.explain import UnknownRule, explain, format_explanation
from rulesets.facts.named_context import named_context
from rulesets.locations import Locations
from rulesets.render.context_render import render_context
from rulesets.render.tree import render_tree
from rulesets.render.tree_writer import Fresh, Stale, check_tree, write_tree
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
from rulesets.source.directory import Present, RulesetsDirectory, read_directory
from rulesets.source.pool import RENDER_DIRECTORY

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
    explaining = commands.add_parser(
        "explain", help="print which manifest lines decided one rule in one named context"
    )
    explaining.add_argument("rule", help="the rule to trace")
    explaining.add_argument("--model", help="the model identifier or declared name of the context")
    explaining.add_argument("--agent", help="the agent type of the context")
    explaining.add_argument(
        "--kind", choices=["session", "delegate", "fork"], help="the context kind"
    )
    explaining.add_argument("--tools", action="append", default=[], help="a tool the context holds")
    explaining.add_argument("--flag", action="append", default=[], help="a flag the context holds")
    explaining.add_argument(
        "--root", type=pathlib.Path, help="the rulesets directory; the configured one by default"
    )
    auditing = commands.add_parser(
        "delivery-check",
        help="recompose each counted delivery of a session and print one line per difference",
    )
    auditing.add_argument(
        "--session", required=True, help="the session whose deliveries are checked"
    )
    auditing.add_argument(
        "--root", type=pathlib.Path, help="the rulesets directory; the configured one by default"
    )
    loading = commands.add_parser(
        "load-check",
        help="print each file the harness loaded that is named for a rule of the pool",
    )
    loading.add_argument("--session", required=True, help="the session whose loads are checked")
    loading.add_argument(
        "--root", type=pathlib.Path, help="the rulesets directory; the configured one by default"
    )
    listing = commands.add_parser(
        "deliveries", help="print one line for each delivery that reached a context"
    )
    listing.add_argument("--session", required=True, help="the session whose deliveries are listed")
    ejecting = commands.add_parser(
        "eject", help="write the base context as one plain file per rule"
    )
    ejecting.add_argument("--out", required=True, type=pathlib.Path, help="the output directory")
    ejecting.add_argument(
        "--root", type=pathlib.Path, help="the rulesets directory; the configured one by default"
    )
    rendering = commands.add_parser(
        "render",
        help="write the composed text one named context receives to --out, or, with no --out, "
        "the render tree",
    )
    mode = rendering.add_mutually_exclusive_group()
    mode.add_argument("--out", type=pathlib.Path, help="the file one context's render goes to")
    mode.add_argument(
        "--check",
        action="store_true",
        help="write nothing; exit 1 where the render tree on disk differs from what render writes",
    )
    rendering.add_argument("--model", help="the model identifier or declared name of the context")
    rendering.add_argument("--agent", help="the agent type of the context")
    rendering.add_argument(
        "--kind", choices=["session", "delegate", "fork"], help="the context kind"
    )
    rendering.add_argument("--tools", action="append", default=[], help="a tool the context holds")
    rendering.add_argument("--flag", action="append", default=[], help="a flag the context holds")
    rendering.add_argument(
        "--root", type=pathlib.Path, help="the rulesets directory; the configured one by default"
    )
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
    if isinstance(action, Clear):
        remove_state(locations, session)
        return 0
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


def _explain(arguments: argparse.Namespace) -> int:
    root = arguments.root or Locations.from_environment(os.environ).rulesets
    directory = read_directory(root)
    manifest = directory.manifest.manifest if isinstance(directory.manifest, Present) else None
    facts = named_context(
        arguments.model, arguments.agent, arguments.kind, arguments.tools, arguments.flag, manifest
    )
    match explain(directory, arguments.rule, facts):
        case UnknownRule(rule):
            print(f"cli.py: the pool holds no rule `{rule}`", file=sys.stderr)
            return 1
        case explanation:
            for line in format_explanation(explanation):
                print(line)
            return 0


def _existing_root(root: pathlib.Path | None) -> pathlib.Path | None:
    """The rulesets directory `root` names, or the configured one; None, after saying so, where none stands."""

    chosen = root or Locations.from_environment(os.environ).rulesets
    if chosen.is_dir():
        return chosen
    print(f"cli.py: no rulesets directory at {chosen}", file=sys.stderr)
    return None


def _eject(arguments: argparse.Namespace) -> int:
    root = _existing_root(arguments.root)
    if root is None:
        return _USAGE_ERROR
    for line in eject(read_directory(root), arguments.out).lines():
        print(line)
    return 0


def _render_tree(directory: RulesetsDirectory, check_only: bool) -> int:
    folder = directory.root / RENDER_DIRECTORY
    tree = render_tree(directory)
    if not check_only:
        write_tree(folder, tree)
        return 0
    match check_tree(folder, tree):
        case Stale(differing):
            for name in differing:
                print(f"{folder / name}: differs from what render writes")
            return 1
        case Fresh():
            return 0


def _render(arguments: argparse.Namespace) -> int:
    root = _existing_root(arguments.root)
    if root is None:
        return _USAGE_ERROR
    directory = read_directory(root)
    if arguments.out is None:
        return _render_tree(directory, arguments.check)
    manifest = directory.manifest.manifest if isinstance(directory.manifest, Present) else None
    facts = named_context(
        arguments.model, arguments.agent, arguments.kind, arguments.tools, arguments.flag, manifest
    )
    composition = compose(directory, facts, SessionState())
    text = render_context(composition, directory.pool)
    arguments.out.write_bytes(text.encode("utf-8"))
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
    if arguments.command == "explain":
        return _explain(arguments)
    if arguments.command == "eject":
        return _eject(arguments)
    if arguments.command == "render":
        return _render(arguments)
    if arguments.command == "delivery-check":
        locations = Locations.from_environment(os.environ)
        root = arguments.root or locations.rulesets
        differences = delivery_check(locations, arguments.session, root)
        for difference in differences:
            print(difference.line())
        return 1 if differences else 0
    if arguments.command == "load-check":
        locations = Locations.from_environment(os.environ)
        root = arguments.root or locations.rulesets
        findings = load_check(locations, arguments.session, root)
        for finding in findings:
            print(finding.line())
        return 1 if findings else 0
    if arguments.command == "deliveries":
        for context in deliveries(Locations.from_environment(os.environ), arguments.session):
            print(context.line())
        return 0
    if not arguments.root.is_dir():
        print(f"cli.py: no rulesets directory at {arguments.root}", file=sys.stderr)
        return _USAGE_ERROR
    report = check(arguments.root)
    for line in report_lines(report):
        print(line)
    return 1 if report.errors else 0


if __name__ == "__main__":
    sys.exit(main())
