"""The body of each rule a composition delivers, read from the pool at its variant."""

from __future__ import annotations

from rulesets.compose.composition import Composition
from rulesets.delivery.parts import Body
from rulesets.source.pool import Pool


def bodies_of(composition: Composition, pool: Pool) -> tuple[Body, ...]:
    """The body of each composed rule at its variant, in composition order, as the file reads."""

    found: list[Body] = []
    for delivered in composition.rules:
        rule = pool.rules[delivered.rule]
        file = rule.variants[delivered.variant] if delivered.variant else rule.default
        if file is None:
            continue
        found.append(Body(delivered.rule, file.text))
    return tuple(found)
