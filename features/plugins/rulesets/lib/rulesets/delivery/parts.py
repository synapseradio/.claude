"""Rule bodies packed into parts that each stay within the part budget."""

from __future__ import annotations

import dataclasses

from rulesets.compose.composition import Composition
from rulesets.part_budget import PART_BUDGET
from rulesets.source.pool import Pool

MAX_PARTS = 10


@dataclasses.dataclass(frozen=True)
class Body:
    """The exact text of a rule file, with a final newline added where it lacks one."""

    rule: str
    text: str


@dataclasses.dataclass(frozen=True)
class Part:
    index: int
    bodies: tuple[Body, ...]


def bodies_of(composition: Composition, pool: Pool) -> tuple[Body, ...]:
    """The body of each composed rule at its variant, in composition order."""

    found: list[Body] = []
    for delivered in composition.rules:
        rule = pool.rules[delivered.rule]
        file = rule.variants[delivered.variant] if delivered.variant else rule.default
        if file is None:
            continue
        text = file.text if file.text.endswith("\n") or not file.text else file.text + "\n"
        found.append(Body(delivered.rule, text))
    return tuple(found)


def pack_parts(bodies: tuple[Body, ...]) -> tuple[Part, ...]:
    """Fill each part in order up to the budget; a body past the budget sits alone in its part."""

    groups: list[list[Body]] = []
    size = 0
    for body in bodies:
        if groups and size + len(body.text) <= PART_BUDGET:
            groups[-1].append(body)
            size += len(body.text)
        else:
            groups.append([body])
            size = len(body.text)
    return tuple(Part(index, tuple(group)) for index, group in enumerate(groups, start=1))
