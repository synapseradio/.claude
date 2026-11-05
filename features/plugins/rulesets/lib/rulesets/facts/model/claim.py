"""Claim a model identifier for the declared name an item's `model` test will match."""

from collections.abc import Iterable

from rulesets.facts.model.fact import (
    Claimed,
    IdentifierSource,
    Missing,
    ModelFact,
    NotAString,
    Unclaimed,
)

CLAIM_PREFIX = "claude-"
CLAIM_BOUNDARIES = "-["


def claim_model(identifier: object, source: IdentifierSource, models: Iterable[str]) -> ModelFact:
    """Claim an identifier, as reported, for a declared name."""

    match identifier:
        case None | "":
            return Missing()
        case str():
            pass
        case _:
            return Missing(NotAString(identifier, source))

    name = claiming_name(identifier, frozenset(models))
    if name is None:
        return Unclaimed(identifier, source)
    return Claimed(name, identifier, source)


def claiming_name(identifier: str, names: frozenset[str]) -> str | None:
    """The longest declared name that claims `identifier`, or None."""

    if identifier in names:
        return identifier
    claiming = [name for name in names if name and opens_on(identifier, name)]
    return max(claiming, key=len, default=None)


def opens_on(identifier: str, name: str) -> bool:
    """Whether `identifier` is `claude-<name>` or continues it at a `-` or `[`."""

    opening = CLAIM_PREFIX + name
    return identifier.startswith(opening) and (
        len(identifier) == len(opening) or identifier[len(opening)] in CLAIM_BOUNDARIES
    )
