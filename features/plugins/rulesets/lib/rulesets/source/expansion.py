"""Expand a list of references into entries and statements.

A list is the sequence of references a manifest writes under `defaults`, a ruleset, or a
`when` item. This module needs only the lists a spread can name and the variants each rule
has, so it reads neither the manifest nor the pool.
"""

from __future__ import annotations

import dataclasses
from collections.abc import Collection, Mapping, Sequence
from typing import assert_never

from rulesets.source.reference import (
    RESERVED_RULESETS,
    EntryForm,
    MalformedTarget,
    Reference,
    RuleTarget,
    SpreadTarget,
    UnquotedTarget,
)


@dataclasses.dataclass(frozen=True)
class Entry:
    """A rule a list adds, at a variant or at none, and the reference that added it."""

    rule: str
    variant: str | None
    source: Reference


@dataclasses.dataclass(frozen=True)
class Removal:
    """A statement a remove makes: an exclusion of the rule where `variant` is None, else a strike."""

    rule: str
    variant: str | None
    source: Reference


@dataclasses.dataclass(frozen=True)
class MalformedReference:
    """A reference that is no reference form. `reason` says what a form looks like."""

    reference: Reference
    reason: str


@dataclasses.dataclass(frozen=True)
class UnquotedReference:
    """A reference written as anything but a quoted string."""

    reference: Reference
    form: EntryForm


@dataclasses.dataclass(frozen=True)
class UnknownRule:
    """A reference to a rule the pool does not hold."""

    reference: Reference
    rule: str


@dataclasses.dataclass(frozen=True)
class UnknownVariant:
    """A reference to a variant the rule does not have."""

    reference: Reference
    rule: str
    variant: str


@dataclasses.dataclass(frozen=True)
class UnknownRuleset:
    """A spread of a ruleset nothing declares."""

    reference: Reference
    ruleset: str


type ReferenceProblem = (
    MalformedReference | UnquotedReference | UnknownRule | UnknownVariant | UnknownRuleset
)


@dataclasses.dataclass(frozen=True)
class Conflict:
    """The entries of one list that set two or more variants of one rule."""

    rule: str
    entries: tuple[Entry, ...]


@dataclasses.dataclass(frozen=True)
class Expansion:
    """What one list says.

    `entries` are the adds left after the list's removes. `removals` are the statements its
    removes make. `problems` are the references the list could not resolve, which contribute
    nothing. `conflicts` are the rules the list sets two variants of.
    """

    entries: tuple[Entry, ...]
    removals: tuple[Removal, ...]
    problems: tuple[ReferenceProblem, ...]
    conflicts: tuple[Conflict, ...]

    @property
    def without_conflicts(self) -> tuple[Entry, ...]:
        """The entries without those that set a variant of a conflicted rule."""

        conflicted = {entry for conflict in self.conflicts for entry in conflict.entries}
        return tuple(entry for entry in self.entries if entry not in conflicted)


def _cycles(lists: Mapping[str, Sequence[Reference]]) -> dict[str, tuple[str, ...]]:
    """Each list that sits in a cycle of spreads, with the sorted names of its cycle."""

    edges = {
        name: [
            reference.target.ruleset
            for reference in references
            if isinstance(reference.target, SpreadTarget) and reference.target.ruleset in lists
        ]
        for name, references in lists.items()
    }
    order: dict[str, int] = {}
    low: dict[str, int] = {}
    stack: list[str] = []
    found: dict[str, tuple[str, ...]] = {}

    def visit(node: str) -> None:
        order[node] = low[node] = len(order)
        stack.append(node)
        for follow in edges[node]:
            if follow not in order:
                visit(follow)
                low[node] = min(low[node], low[follow])
            elif follow in stack:
                low[node] = min(low[node], order[follow])
        if low[node] != order[node]:
            return
        members = stack[stack.index(node) :]
        del stack[stack.index(node) :]
        if len(members) > 1 or node in edges[node]:
            found.update({member: tuple(sorted(members)) for member in members})

    for name in lists:
        if name not in order:
            visit(name)
    return found


class Expander:
    """Expands lists of references.

    `lists` maps each name a spread can reach to its references, `defaults` among them.
    `rules` maps each rule of the pool to its variants, in the order `all:*` spreads them.
    A spread of a list that sits in a cycle of spreads reaches no rule.
    """

    def __init__(
        self, lists: Mapping[str, Sequence[Reference]], rules: Mapping[str, Collection[str]]
    ):
        self._lists = lists
        self._rules = rules
        self._cycles = _cycles(lists)
        self._spreads: dict[str, tuple[tuple[str, str | None], ...]] = {}

    def cycle_of(self, name: str) -> tuple[str, ...]:
        """The sorted names of the cycle of spreads that holds the list, or ()."""

        return self._cycles.get(name, ())

    def route_to(self, ruleset: str, rule: str) -> tuple[str, ...]:
        """The rulesets from `ruleset` down to the one that names `rule`, `ruleset` first.

        A ruleset that is reserved, undeclared, or in a cycle, or that holds no add of the rule,
        ends the route.
        """

        if ruleset not in self._lists or ruleset in self._cycles:
            return (ruleset,)
        held = next(
            (e for e in self.expand(self._lists[ruleset]).without_conflicts if e.rule == rule),
            None,
        )
        if held is not None and isinstance(held.source.target, SpreadTarget):
            return (ruleset, *self.route_to(held.source.target.ruleset, rule))
        return (ruleset,)

    def _spread(self, name: str) -> tuple[tuple[str, str | None], ...]:
        if name in ("all", "rules"):
            return tuple((rule, None) for rule in self._rules)
        if name not in self._lists or name in self._cycles:
            return ()
        if name not in self._spreads:
            kept = self.expand(self._lists[name]).without_conflicts
            self._spreads[name] = tuple(dict.fromkeys((e.rule, e.variant) for e in kept))
        return self._spreads[name]

    def _unresolved(
        self, reference: Reference, target: SpreadTarget | RuleTarget
    ) -> ReferenceProblem | None:
        match target:
            case SpreadTarget(ruleset):
                known = ruleset in RESERVED_RULESETS or ruleset in self._lists
                return None if known else UnknownRuleset(reference, ruleset)
            case RuleTarget(rule, variant):
                if rule not in self._rules:
                    return UnknownRule(reference, rule)
                if variant is not None and variant not in self._rules[rule]:
                    return UnknownVariant(reference, rule, variant)
                return None
            case _:
                assert_never(target)

    def problems_reached(self, references: Sequence[Reference]) -> tuple[ReferenceProblem, ...]:
        """The problems of a list and of every ruleset it spreads, each ruleset counted once."""

        found: list[ReferenceProblem] = []
        pending = [references]
        seen: set[str] = set()
        while pending:
            current = pending.pop(0)
            found.extend(self.expand(current).problems)
            for reference in current:
                target = reference.target
                if (
                    isinstance(target, SpreadTarget)
                    and target.ruleset in self._lists
                    and target.ruleset not in self._cycles
                    and target.ruleset not in seen
                ):
                    seen.add(target.ruleset)
                    pending.append(self._lists[target.ruleset])
        return tuple(found)

    def expand(self, references: Sequence[Reference]) -> Expansion:
        """Expand one list, applying every remove after every add."""

        adds: list[Entry] = []
        removals: list[Removal] = []
        problems: list[ReferenceProblem] = []
        for reference in references:
            target = reference.target
            match target:
                case MalformedTarget(reason):
                    problems.append(MalformedReference(reference, reason))
                    continue
                case UnquotedTarget(form):
                    problems.append(UnquotedReference(reference, form))
                    continue
                case SpreadTarget() | RuleTarget():
                    if (problem := self._unresolved(reference, target)) is not None:
                        problems.append(problem)
                        continue
            match target:
                case SpreadTarget(ruleset) if reference.remove:
                    reached = dict.fromkeys(rule for rule, _ in self._spread(ruleset))
                    removals.extend(Removal(rule, None, reference) for rule in reached)
                case SpreadTarget(ruleset):
                    adds.extend(Entry(r, v, reference) for r, v in self._spread(ruleset))
                case RuleTarget(rule, variant) if reference.remove:
                    removals.append(Removal(rule, variant, reference))
                case RuleTarget(rule, variant):
                    adds.append(Entry(rule, variant, reference))

        excluded = {removal.rule for removal in removals if removal.variant is None}
        struck = {(removal.rule, removal.variant) for removal in removals if removal.variant}
        entries: dict[tuple[str, str | None], Entry] = {}
        for entry in adds:
            if entry.rule in excluded:
                continue
            if (entry.rule, entry.variant) in struck:
                entry = dataclasses.replace(entry, variant=None)
            entries.setdefault((entry.rule, entry.variant), entry)

        setters: dict[str, list[Entry]] = {}
        for entry in entries.values():
            if entry.variant is not None:
                setters.setdefault(entry.rule, []).append(entry)
        conflicts = tuple(
            Conflict(rule, tuple(setting)) for rule, setting in setters.items() if len(setting) > 1
        )
        return Expansion(tuple(entries.values()), tuple(removals), tuple(problems), conflicts)
