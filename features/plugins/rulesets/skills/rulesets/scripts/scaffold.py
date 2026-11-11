#!/usr/bin/env python3
"""Write a starter rulesets directory: a config, one example rule, and its render.

Usage: scaffold.py [--root DIR]

The root may be missing, empty, or the empty directory a first session creates, whose config
declares nothing and whose pool holds no rule. Any other directory is refused with exit 2 and
left as it was.
"""

import argparse
import os
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "lib"))

from rulesets.locations import Locations
from rulesets.render.tree import render_tree
from rulesets.render.tree_writer import write_tree
from rulesets.source.config import CONFIG_FILE, ConfigParseError, read_config
from rulesets.source.directory import read_directory
from rulesets.source.pool import RENDER_DIRECTORY

_USAGE_ERROR = 2

_CONFIG = "models:\nflags:\ndefaults: all.*\n"

_EXAMPLE = """\
Replace this text with a rule of your own, and give the file the name you want the rule to have.
Each file in this folder holds one rule, and the config decides which contexts receive it.
"""


def _declares_nothing(root: pathlib.Path) -> bool:
    try:
        config = read_config(root)
    except ConfigParseError:
        return False
    return not (
        config.models
        or config.flags
        or (config.defaults and config.defaults.references)
        or config.rulesets
        or config.blocks
        or config.problems
    )


def _empty(root: pathlib.Path) -> bool:
    """Whether the root is missing, empty, or a first session's empty directory."""

    if not root.exists():
        return True
    entries = {entry.name for entry in root.iterdir()}
    if not entries:
        return True
    rules = root / "rules"
    return (
        entries <= {CONFIG_FILE, "rules"}
        and CONFIG_FILE in entries
        and (not rules.exists() or (rules.is_dir() and not any(rules.iterdir())))
        and _declares_nothing(root)
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="scaffold.py", description=__doc__.splitlines()[0])
    parser.add_argument("--root", type=pathlib.Path, help="the rulesets directory to write")
    arguments = parser.parse_args(argv)
    root = arguments.root or Locations.from_environment(os.environ).rulesets
    if not _empty(root):
        print(
            f"scaffold.py: {root} holds files; scaffold writes only into an empty directory",
            file=sys.stderr,
        )
        return _USAGE_ERROR
    (root / "rules").mkdir(parents=True, exist_ok=True)
    (root / CONFIG_FILE).write_text(_CONFIG, encoding="utf-8")
    (root / "rules" / "example.md").write_text(_EXAMPLE, encoding="utf-8")
    write_tree(root / RENDER_DIRECTORY, render_tree(read_directory(root)))
    for path in (CONFIG_FILE, "rules/example.md", f"{RENDER_DIRECTORY}/"):
        print(f"wrote {root / path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
