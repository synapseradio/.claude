#!/usr/bin/env python3.14
"""Own the `instructions` key inside opencode's hand-written `opencode.json`.

opencode's `instructions` array lists rule files rather than holding their
text, so it lives inside a file the user hand-writes rather than in a file
this checkout generates whole. This job owns that one key and leaves every
other key in the file as it found it, key order included.

`--check` compares without writing and exits nonzero where the key differs
from what a write would produce, naming the owning path.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from projection import (
    DEFAULT_TARGETS,
    GeneratedKey,
    Plan,
    Targets,
    apply_plan,
    home_relative,
    unconditional_rules,
)


def rule_instructions(rules_dir: Path) -> list[str]:
    """The `instructions` entries opencode reads the session-wide rules from.

    Each names its canonical path under `~/.claude/rulesets/default/`, so an
    edit to a rule reaches opencode with no run of this job.
    """

    return [home_relative(rule) for rule in unconditional_rules(rules_dir)]


def build_plan(targets: Targets = DEFAULT_TARGETS) -> Plan:
    keys = (
        GeneratedKey(
            targets.opencode_config,
            "instructions",
            rule_instructions(targets.rules_dir),
            after="$schema",
        ),
    )
    return Plan(files=(), keys=keys, dropped=())


def main(argv: list[str] | None = None, targets: Targets = DEFAULT_TARGETS) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="write nothing; exit nonzero when the owned key is out of date",
    )
    args = parser.parse_args(argv)
    return apply_plan(build_plan(targets), check=args.check)


if __name__ == "__main__":
    raise SystemExit(main())
