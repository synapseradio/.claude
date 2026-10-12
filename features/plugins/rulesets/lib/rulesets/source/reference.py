"""Parse the reference forms a manifest list is written in.

A list is the sequence of references a manifest writes under `defaults`, a ruleset, or a
`when` item. Parsing here reads the text of one reference and judges nothing about whether
the rule or ruleset it names exists. Every entry of a list is a quoted string, and an entry
written any other way is a reference of its own kind, so a caller reports it.
"""

from __future__ import annotations

import dataclasses
from typing import Literal

RESERVED_RULESETS = ("defaults", "all", "rules", "none")
_NOT_A_FORM = "not a reference form; write a rule, rule@variant, rules:rule, or ruleset:*"


@dataclasses.dataclass(frozen=True)
class RuleTarget:
    rule: str
    variant: str | None


@dataclasses.dataclass(frozen=True)
class SpreadTarget:
    ruleset: str


@dataclasses.dataclass(frozen=True)
class MalformedTarget:
    reason: str


type EntryForm = Literal["plain", "mapping", "list"]


@dataclasses.dataclass(frozen=True)
class UnquotedTarget:
    """A list entry that is no quoted string: a plain scalar, a mapping, or a nested list."""

    form: EntryForm


type Target = RuleTarget | SpreadTarget | MalformedTarget | UnquotedTarget


@dataclasses.dataclass(frozen=True)
class Reference:
    """One reference as written: its text with any `-`, its file line, and what it names."""

    text: str
    line: int
    remove: bool
    target: Target


def parse_reference(text: str, line: int) -> Reference:
    """Parse one reference as written: `voice`, `rules:voice`, `voice@terse`, `code:*`, or `*`.

    `*` alone spreads every rule of the pool, as `all:*` does. Any form may open with `-` to
    remove what it adds. Text that is no form parses to a MalformedTarget, so a caller
    reports it instead of catching an exception.
    """

    remove = text.startswith("-")
    body = text.removeprefix("-")
    target: Target
    if body == "*":
        target = SpreadTarget("all")
    elif body.endswith(":*"):
        ruleset = body.removesuffix(":*")
        valid = ruleset and ":" not in ruleset
        target = SpreadTarget(ruleset) if valid else MalformedTarget(_NOT_A_FORM)
    else:
        name = body.removeprefix("rules:")
        rule, at, variant = name.partition("@")
        if not rule or ":" in name or (at and not variant):
            target = MalformedTarget(_NOT_A_FORM)
        else:
            target = RuleTarget(rule, variant or None)
    return Reference(text=text, line=line, remove=remove, target=target)


def unquoted_reference(text: str, line: int, form: EntryForm) -> Reference:
    """A list entry written as anything but a quoted string, kept as written."""

    return Reference(text=text, line=line, remove=False, target=UnquotedTarget(form))
