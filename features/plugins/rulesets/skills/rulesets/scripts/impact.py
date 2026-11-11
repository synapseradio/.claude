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
import dataclasses
import itertools
import os
import pathlib
import shutil
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "lib"))

from rulesets.compose.composition import compose
from rulesets.facts.named_context import named_context
from rulesets.locations import Locations
from rulesets.session.state import SessionState
from rulesets.source.condition import ConditionError, fact_tests, parse_condition
from rulesets.source.config import CONFIG_FILE
from rulesets.source.directory import Present, RulesetsDirectory, read_directory

_USAGE_ERROR = 2
_SOURCE = "source"
_COMPOSITIONS = "compositions.txt"
_KINDS = ("session", "delegate")
_NONE = "-"


@dataclasses.dataclass(frozen=True)
class Context:
    """One context of the matrix; None leaves that fact absent, or no flag set."""

    kind: str
    model: str | None
    agent: str | None
    flag: str | None
    tool: str | None

    def label(self) -> str:
        return " ".join(
            f"{name}={value or _NONE}"
            for name, value in (
                ("kind", self.kind),
                ("model", self.model),
                ("agent", self.agent),
                ("flag", self.flag),
                ("tools", self.tool),
            )
        )


type Received = dict[str, str | None]


def _tested(directory: RulesetsDirectory, fact: str) -> set[str]:
    """The values a `when` condition tests the fact against."""

    if not isinstance(directory.config, Present):
        return set()
    values: set[str] = set()
    for block in directory.config.config.blocks:
        try:
            condition = parse_condition(block.condition)
        except ConditionError:
            continue
        values |= {test.value for test in fact_tests(condition) if test.fact == fact}
    return values


def _declared(directory: RulesetsDirectory) -> tuple[set[str], set[str]]:
    if not isinstance(directory.config, Present):
        return set(), set()
    config = directory.config.config
    return set(config.models), set(config.flags)


def contexts(*directories: RulesetsDirectory) -> list[Context]:
    """The matrix the directories' configs name between them, each fact's values in order."""

    models: set[str] = set()
    flags: set[str] = set()
    agents: set[str] = set()
    tools: set[str] = set()
    for directory in directories:
        declared_models, declared_flags = _declared(directory)
        models |= declared_models
        flags |= declared_flags
        agents |= _tested(directory, "agent")
        tools |= _tested(directory, "tools")

    def with_none(values: set[str]) -> list[str | None]:
        return [None, *sorted(values)]

    return [
        Context(kind, model, agent, flag, tool)
        for kind, model, agent, flag, tool in itertools.product(
            _KINDS, with_none(models), with_none(agents), with_none(flags), with_none(tools)
        )
    ]


def received(directory: RulesetsDirectory, context: Context) -> Received:
    """Each rule the context receives, with its variant (None for the default form)."""

    config = directory.config.config if isinstance(directory.config, Present) else None
    facts = named_context(
        context.model,
        context.agent,
        context.kind,
        [context.tool] if context.tool else [],
        [context.flag] if context.flag else [],
        config,
    )
    return {rule.rule: rule.variant for rule in compose(directory, facts, SessionState()).rules}


def _form(rule: str, variant: str | None) -> str:
    return f"{rule}@{variant}" if variant else rule


def differences(before: Received, after: Received) -> list[str]:
    lines: list[str] = []
    for rule in sorted(before.keys() | after.keys()):
        if rule not in before:
            lines.append(f"  + {_form(rule, after[rule])}")
        elif rule not in after:
            lines.append(f"  - {_form(rule, before[rule])}")
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
        f"{context.label()}\t{' '.join(_form(r, v) for r, v in received(directory, context).items()) or _NONE}"
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
