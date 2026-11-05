"""The order of positions, and each rule's outcome from the statements about it.

Only this module constructs or compares a position.
"""

from __future__ import annotations

import dataclasses
import enum

from rulesets.compose.origin import Origin
from rulesets.facts.kinds import Rank
from rulesets.source.reference import Reference, RuleTarget


class PositionBand(enum.IntEnum):
    DIRECTORY = 0
    SESSION = 1


class Reach(enum.IntEnum):
    """Whether a statement reaches its rule through a ruleset or names it."""

    THROUGH_RULESET = 0
    NAMED = 1


@dataclasses.dataclass(frozen=True, order=True)
class Position:
    """Band, then rank, then reach: the first difference decides."""

    band: PositionBand
    rank: Rank
    reach: Reach


def position(band: PositionBand, rank: Rank, source: Reference) -> Position:
    """The position of a statement a reference makes in a list standing at `band` and `rank`."""

    reach = Reach.NAMED if isinstance(source.target, RuleTarget) else Reach.THROUGH_RULESET
    return Position(band, rank, reach)


@dataclasses.dataclass(frozen=True)
class Adds:
    """Includes the rule, and sets `variant` where it is not None."""

    variant: str | None


@dataclasses.dataclass(frozen=True)
class Removes:
    """Excludes the rule."""


@dataclasses.dataclass(frozen=True)
class Strikes:
    """Strikes `variant`, leaving inclusion as it was."""

    variant: str


type Says = Adds | Removes | Strikes


@dataclasses.dataclass(frozen=True)
class Statement:
    rule: str
    says: Says
    position: Position
    source: Reference
    origin: Origin


@dataclasses.dataclass(frozen=True)
class Included:
    """The rule is on; `winner` is the add that decided it."""

    winner: Statement


@dataclasses.dataclass(frozen=True)
class Excluded:
    """The rule is off; `winner` is the remove that decided it."""

    winner: Statement


class Unreached:
    pass


type Inclusion = Included | Excluded | Unreached


def _by_strength(statement: Statement) -> tuple[Position, bool]:
    return statement.position, isinstance(statement.says, Removes)


def inclusion_statements(statements: tuple[Statement, ...]) -> tuple[Statement, ...]:
    """The adds and removes about a rule, from the weakest to the strongest, ties in written order."""

    return tuple(
        sorted(
            (s for s in statements if isinstance(s.says, Adds | Removes)),
            key=_by_strength,
        )
    )


def inclusion(statements: tuple[Statement, ...]) -> Inclusion:
    """The highest position decides, and an exclude beats an include at one position."""

    deciding = inclusion_statements(statements)
    if not deciding:
        return Unreached()
    winner = deciding[-1]
    return Excluded(winner) if isinstance(winner.says, Removes) else Included(winner)


@dataclasses.dataclass(frozen=True)
class VariantConflict:
    """Statements at one position that set different variants of one rule, none struck there."""

    rule: str
    position: Position
    statements: tuple[Statement, ...]


@dataclasses.dataclass(frozen=True)
class VariantOutcome:
    """The variant a rule takes (None: the default form), the add that set it, and the conflict
    delivery fell back from."""

    variant: str | None
    conflict: VariantConflict | None
    winner: Statement | None


@dataclasses.dataclass(frozen=True)
class _Layer:
    """The set statements at one position that no strike at that position or higher names."""

    position: Position
    sets: tuple[Statement, ...]

    @property
    def variants(self) -> set[str]:
        return {
            statement.says.variant
            for statement in self.sets
            if isinstance(statement.says, Adds) and statement.says.variant is not None
        }


def _layers(statements: tuple[Statement, ...]) -> list[_Layer]:
    """The positions of the statements, highest first, each with its standing sets."""

    layers: list[_Layer] = []
    struck: set[str] = set()
    for where in sorted({statement.position for statement in statements}, reverse=True):
        here = [statement for statement in statements if statement.position == where]
        struck |= {s.says.variant for s in here if isinstance(s.says, Strikes)}
        sets = tuple(
            s
            for s in here
            if isinstance(s.says, Adds)
            and s.says.variant is not None
            and s.says.variant not in struck
        )
        layers.append(_Layer(where, sets))
    return layers


def _conflict(rule: str, layer: _Layer) -> VariantConflict:
    return VariantConflict(rule, layer.position, layer.sets)


def conflicts(statements: tuple[Statement, ...]) -> tuple[VariantConflict, ...]:
    """Every position of one rule's statements where the standing sets name different variants."""

    return tuple(
        _conflict(statements[0].rule, layer)
        for layer in _layers(statements)
        if len(layer.variants) > 1
    )


def variant(statements: tuple[Statement, ...]) -> VariantOutcome:
    """The variant of the highest position whose standing sets agree, else the default form.

    A position whose sets disagree is a conflict. The highest one is reported, and the rule
    takes the variant of the next position down whose sets agree.
    """

    found: VariantConflict | None = None
    for layer in _layers(statements):
        if len(layer.variants) > 1:
            found = found or _conflict(statements[0].rule, layer)
        elif layer.variants:
            return VariantOutcome(next(iter(layer.variants)), found, layer.sets[-1])
    return VariantOutcome(None, found, None)
