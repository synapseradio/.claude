"""One context's composed text, each rule's bytes under a marker line."""

from __future__ import annotations

from rulesets.compose.composition import Composition
from rulesets.delivery.rule_bodies import bodies_of
from rulesets.source.marker import marker
from rulesets.source.pool import Pool

SECTION_SEPARATOR = "\n"


def render_context(composition: Composition, pool: Pool) -> str:
    """The composed rules in composition order, each preceded by its marker line.

    The text after a marker is the rule file's bytes. One separator line break stands before
    every marker after the first, so the split reads each body back whether or not it ends in a
    line break. This text is not the text delivery sends.
    """

    bodies = bodies_of(composition, pool)
    return SECTION_SEPARATOR.join(
        f"{marker(delivered.rule, delivered.variant)}\n{body.text}"
        for delivered, body in zip(composition.rules, bodies, strict=True)
    )
