#!/usr/bin/env python3
"""Command line for the rulesets engine: `check --root <dir>`.

This module parses arguments, prints, and sets the exit status. Every finding comes from
`rulesets.check.run`, and every line's wording from `rulesets.check.report_format`.
"""

import argparse
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from rulesets.check.report_format import report_lines
from rulesets.check.run import check

USAGE_ERROR = 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="cli.py", description=__doc__.splitlines()[0])
    commands = parser.add_subparsers(dest="command", required=True)
    checking = commands.add_parser(
        "check",
        help="print every error and warning of a rulesets directory; exit 1 only on an error",
    )
    checking.add_argument("--root", required=True, type=pathlib.Path, help="the rulesets directory")
    return parser


def main(argv: list[str] | None = None) -> int:
    arguments = build_parser().parse_args(argv)
    if not arguments.root.is_dir():
        print(f"cli.py: no rulesets directory at {arguments.root}", file=sys.stderr)
        return USAGE_ERROR
    report = check(arguments.root)
    for line in report_lines(report):
        print(line)
    return 1 if report.errors else 0


if __name__ == "__main__":
    sys.exit(main())
