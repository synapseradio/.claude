"""Rule bodies packed into parts that each stay within the part budget."""

from __future__ import annotations

import dataclasses

from rulesets.part_budget import PART_BUDGET
from rulesets.source.marker import delivered

MAX_PARTS = 10


@dataclasses.dataclass(frozen=True)
class Body:
    """The exact text of a rule file."""

    rule: str
    text: str

    @property
    def delivered(self) -> str:
        """The text a context receives for the rule: its marker, a blank line, then the body."""

        return delivered(self.rule, self.text)


@dataclasses.dataclass(frozen=True)
class Part:
    index: int
    bodies: tuple[Body, ...]

    @property
    def text(self) -> str:
        """The text the part's hook entry delivers."""

        return "".join(body.delivered for body in self.bodies)


def pack_parts(bodies: tuple[Body, ...]) -> tuple[Part, ...]:
    """Fill each part in order up to the budget, counting each marker; no body outgrows the budget."""

    groups: list[list[Body]] = []
    size = 0
    for body in bodies:
        if groups and size + len(body.delivered) <= PART_BUDGET:
            groups[-1].append(body)
            size += len(body.delivered)
        else:
            groups.append([body])
            size = len(body.delivered)
    return tuple(Part(index, tuple(group)) for index, group in enumerate(groups, start=1))
