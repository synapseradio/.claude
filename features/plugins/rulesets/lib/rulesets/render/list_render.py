"""The text of a render that holds a given set of rules, each at one variant."""

from __future__ import annotations

from collections.abc import Mapping

from rulesets.compose.composition import Composition, DeliveredRule
from rulesets.render.context_render import render_context
from rulesets.source.pool import Pool

type Held = Mapping[str, str | None]
"""Each rule a render holds, with the variant it holds it at (None: the default form)."""


def render_held(held: Held, pool: Pool) -> str:
    """The render of `held`, rules sorted by name."""

    rules = tuple(DeliveredRule(rule, variant) for rule, variant in sorted(held.items()))
    return render_context(Composition(rules=rules, conflicts=()), pool)
