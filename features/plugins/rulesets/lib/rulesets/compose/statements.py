"""Applied lists turned into the statements they make about rules."""

from __future__ import annotations

from rulesets.compose.applying import AppliedList
from rulesets.compose.precedence import Adds, Removes, Statement, Strikes, position
from rulesets.source.expansion import Expander


def statements(applied: tuple[AppliedList, ...], expander: Expander) -> tuple[Statement, ...]:
    """Each add left after the list's removes includes its rule, and sets its variant where named.

    Each remove excludes the rules it reaches, or strikes the variant it names.
    """

    made: list[Statement] = []
    for applying in applied:
        expansion = expander.expand(applying.references)
        for entry in expansion.entries:
            where = position(applying.band, applying.rank, entry.source)
            made.append(
                Statement(entry.rule, Adds(entry.variant), where, entry.source, applying.origin)
            )
        for removal in expansion.removals:
            where = position(applying.band, applying.rank, removal.source)
            says = Removes() if removal.variant is None else Strikes(removal.variant)
            made.append(Statement(removal.rule, says, where, removal.source, applying.origin))
    return tuple(made)
