"""Rule bodies packed into parts that each stay within the part budget."""

from __future__ import annotations

import dataclasses

from rulesets.part_budget import PART_BUDGET

MAX_PARTS = 10


@dataclasses.dataclass(frozen=True)
class Body:
    """The exact text of a rule file."""

    rule: str
    text: str


@dataclasses.dataclass(frozen=True)
class Part:
    index: int
    bodies: tuple[Body, ...]


def pack_parts(bodies: tuple[Body, ...]) -> tuple[Part, ...]:
    """Fill each part in order up to the budget; no body is longer than the budget."""

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
