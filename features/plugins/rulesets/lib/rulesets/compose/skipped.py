"""The references of the applying lists that name something undeclared, which contribute nothing."""

from __future__ import annotations

import dataclasses

from rulesets.compose.applying import AppliedList
from rulesets.source.expansion import Expander, UnknownRule, UnknownRuleset, UnknownVariant


@dataclasses.dataclass(frozen=True)
class SkippedReference:
    """A reference to an undeclared rule, variant, or ruleset, which contributed nothing."""

    text: str
    line: int
    name: str


def skipped_references(
    applied: tuple[AppliedList, ...], expander: Expander
) -> tuple[SkippedReference, ...]:
    """The references of the applying lists that name something undeclared, once each."""

    found: dict[tuple[str, int], SkippedReference] = {}
    for applying in applied:
        for problem in expander.problems_reached(applying.references):
            match problem:
                case UnknownRule(reference, name) | UnknownRuleset(reference, name):
                    pass
                case UnknownVariant(reference, rule, variant):
                    name = f"{rule}@{variant}"
                case _:
                    continue
            found.setdefault(
                (reference.text, reference.line),
                SkippedReference(reference.text, reference.line, name),
            )
    return tuple(found.values())
