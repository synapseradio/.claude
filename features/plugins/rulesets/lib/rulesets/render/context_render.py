"""One context's composed text, each rule's bytes under a marker line."""

from __future__ import annotations

from rulesets.compose.composition import Composition
from rulesets.delivery.rule_bodies import bodies_of
from rulesets.source.marker import marker
from rulesets.source.pool import Pool


def render_context(composition: Composition, pool: Pool) -> str:
    """The composed rules in composition order, each preceded by its marker line.

    The text after a marker is the rule file's bytes, the same text delivery sends.
    """

    bodies = bodies_of(composition, pool)
    return "".join(
        f"{marker(delivered.rule, delivered.variant)}\n{body.text}"
        for delivered, body in zip(composition.rules, bodies, strict=True)
    )
