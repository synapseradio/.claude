"""A context built from facts a person names, for the tools that trace or render one context."""

from __future__ import annotations

from collections.abc import Iterable

from rulesets.facts.context import ABSENT, UNCLAIMED, Facts, Kind, ListedTools
from rulesets.facts.model.claim import claiming_name
from rulesets.source.manifest import Manifest


def named_context(
    model: str | None,
    agent: str | None,
    kind: Kind | None,
    tools: Iterable[str],
    flags: Iterable[str],
    manifest: Manifest | None,
) -> Facts:
    """The facts a person names. A fact left unnamed is absent, and flags left unnamed are unset.

    A model names itself where a declared name equals it or is the name it opens on, as a
    delivery claims an identifier. No tool named leaves the tools fact absent.
    """

    held = frozenset(tools)
    declared = manifest.models if manifest else ()
    claimed = (claiming_name(model, frozenset(declared)) or UNCLAIMED) if model else ABSENT
    return Facts(
        model=claimed,
        agent=agent or ABSENT,
        kind=kind or ABSENT,
        flags=frozenset(flags),
        tools=ListedTools(held) if held else ABSENT,
    )
