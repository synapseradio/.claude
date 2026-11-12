#!/usr/bin/env python3
"""Show what an edit to a rulesets directory changes in each context it composes for.

Usage:
  impact.py snapshot [--root DIR] --out SNAPSHOT
  impact.py diff BEFORE AFTER

`snapshot` copies the config and the pool to SNAPSHOT/source and writes each context's
composition to SNAPSHOT/compositions.txt. `diff` composes both snapshots over the contexts
either config names and prints, for each context that differs, the rules added (+), removed
(-), or set to another variant (~). It prints nothing where no context differs.

The contexts cross each kind (session, delegate); each declared model, and no model; each agent
a `when` condition tests, and no agent; no flag, and each declared flag on its own; and no tool,
and each tool a `when` condition tests.
"""

import argparse
import os
import pathlib
import shutil
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "lib"))

from rulesets.context_matrix import NONE, Received, contexts, form, received
from rulesets.locations import Locations
from rulesets.source.config import CONFIG_FILE
from rulesets.source.directory import read_directory

_USAGE_ERROR = 2
_SOURCE = "source"
_COMPOSITIONS = "compositions.txt"


def differences(before: Received, after: Received) -> list[str]:
    lines: list[str] = []
    for rule in sorted(before.keys() | after.keys()):
        if rule not in before:
            lines.append(f"  + {form(rule, after[rule])}")
        elif rule not in after:
            lines.append(f"  - {form(rule, before[rule])}")
        elif before[rule] != after[rule]:
            was, now = (variant or "default" for variant in (before[rule], after[rule]))
            lines.append(f"  ~ {rule}: {was} -> {now}")
    return lines


def snapshot(root: pathlib.Path, out: pathlib.Path) -> int:
    if not root.is_dir():
        print(f"impact.py: no rulesets directory at {root}", file=sys.stderr)
        return _USAGE_ERROR
    if out.exists() and any(out.iterdir()):
        print(f"impact.py: {out} holds files; a snapshot goes to a new directory", file=sys.stderr)
        return _USAGE_ERROR
    source = out / _SOURCE
    source.mkdir(parents=True)
    if (root / CONFIG_FILE).is_file():
        shutil.copy2(root / CONFIG_FILE, source / CONFIG_FILE)
    if (root / "rules").is_dir():
        shutil.copytree(root / "rules", source / "rules")
    directory = read_directory(source)
    lines = [
        f"{context.label()}\t{' '.join(form(r, v) for r, v in received(directory, context).items()) or NONE}"
        for context in contexts(directory)
    ]
    (out / _COMPOSITIONS).write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {out}")
    return 0


def diff(before_snapshot: pathlib.Path, after_snapshot: pathlib.Path) -> int:
    for path in (before_snapshot, after_snapshot):
        if not (path / _SOURCE).is_dir():
            print(f"impact.py: {path} is no snapshot", file=sys.stderr)
            return _USAGE_ERROR
    before = read_directory(before_snapshot / _SOURCE)
    after = read_directory(after_snapshot / _SOURCE)
    for context in contexts(before, after):
        lines = differences(received(before, context), received(after, context))
        if lines:
            print(context.label())
            print("\n".join(lines))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="impact.py", description=__doc__.splitlines()[0])
    commands = parser.add_subparsers(dest="command", required=True)
    taking = commands.add_parser("snapshot", help="record the directory and its compositions")
    taking.add_argument("--root", type=pathlib.Path, help="the rulesets directory")
    taking.add_argument("--out", required=True, type=pathlib.Path, help="a new directory")
    comparing = commands.add_parser("diff", help="print each context two snapshots differ in")
    comparing.add_argument("before", type=pathlib.Path)
    comparing.add_argument("after", type=pathlib.Path)
    arguments = parser.parse_args(argv)
    if arguments.command == "snapshot":
        root = arguments.root or Locations.from_environment(os.environ).rulesets
        return snapshot(root, arguments.out)
    return diff(arguments.before, arguments.after)


if __name__ == "__main__":
    sys.exit(main())
