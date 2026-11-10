#!/usr/bin/env python3
"""Run the checks a rulesets directory must pass before a commit, stopping at the first that fails.

Usage: gate.py [--root DIR]

The steps are `check`, which prints every error and warning, and `render --check`, which
renders the tree in memory and compares it with `-render/`. The gate writes nothing. It exits 0
when every step passes, 1 when a step fails, and 2 when no rulesets directory stands at the root.
"""

import argparse
import os
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "lib"))

from rulesets import cli
from rulesets.locations import Locations

_USAGE_ERROR = 2


def _steps(root: pathlib.Path) -> tuple[tuple[str, list[str]], ...]:
    return (
        ("check", ["check", "--root", str(root)]),
        ("render --check", ["render", "--check", "--root", str(root)]),
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="gate.py", description=__doc__.splitlines()[0])
    parser.add_argument("--root", type=pathlib.Path, help="the rulesets directory")
    arguments = parser.parse_args(argv)
    root = arguments.root or Locations.from_environment(os.environ).rulesets
    if not root.is_dir():
        print(f"gate.py: no rulesets directory at {root}", file=sys.stderr)
        return _USAGE_ERROR
    for name, words in _steps(root):
        status = cli.main(words)
        if status != 0:
            hint = " (run render, then the gate again)" if name == "render --check" else ""
            print(f"gate: stopped at {name}{hint}")
            return 1
    print("gate: passed check and render --check")
    return 0


if __name__ == "__main__":
    sys.exit(main())
