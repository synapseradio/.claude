"""The facts a context's conditions can test."""

from dataclasses import dataclass
from enum import Enum
from typing import Literal

type Kind = Literal["session", "delegate"]


class Absent(Enum):
    """A fact the context does not carry; every test over it evaluates unknown."""

    ABSENT = "absent"


class NoClaim(Enum):
    """A model identifier that no declared name claims; every `model` test over it is false."""

    UNCLAIMED = "unclaimed"


ABSENT = Absent.ABSENT
UNCLAIMED = NoClaim.UNCLAIMED


@dataclass(frozen=True)
class ListedTools:
    """The tools a definition lists, less those it disallows."""

    tools: frozenset[str]

    def holds(self, tool: str) -> bool:
        return tool in self.tools


@dataclass(frozen=True)
class AllToolsBut:
    """Every tool, less those a definition with no tools list disallows."""

    removed: frozenset[str]

    def holds(self, tool: str) -> bool:
        return tool not in self.removed


@dataclass(frozen=True)
class Facts:
    """What a `when` item's condition can test in one context.

    `model` is the declared name that claimed the context's model identifier,
    UNCLAIMED where no name claimed it, and ABSENT where the identifier is missing.
    `agent`, `kind`, `tools`, and `session` are ABSENT where the context carries no such fact.
    """

    model: str | NoClaim | Absent
    agent: str | Absent
    kind: Kind | Absent
    flags: frozenset[str]
    session: str | Absent = ABSENT
    tools: ListedTools | AllToolsBut | Absent = ABSENT
