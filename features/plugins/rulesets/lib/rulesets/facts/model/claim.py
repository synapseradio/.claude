"""Claim a model identifier for the declared name an item's `model` test will match."""

from collections.abc import Iterable, Mapping

from rulesets.facts.model.fact import (
    Claimed,
    Missing,
    ModelFact,
    ModelSource,
    NotAString,
    Unclaimed,
)

CLAIM_PREFIX = "claude-"
CLAIM_BOUNDARIES = "-["

# Each alias is the middle of its profile variable's name, so the engine names the
# variables and no model.
PROFILE_VARIABLE_PREFIX = "ANTHROPIC_DEFAULT_"
PROFILE_VARIABLES = (
    "ANTHROPIC_DEFAULT_OPUS_MODEL",
    "ANTHROPIC_DEFAULT_SONNET_MODEL",
    "ANTHROPIC_DEFAULT_HAIKU_MODEL",
    "ANTHROPIC_DEFAULT_FABLE_MODEL",
)


def claim_model(
    identifier: object,
    source: ModelSource,
    models: Iterable[str],
    env: Mapping[str, str],
) -> ModelFact:
    """Claim an identifier for a declared name, resolving an alias through its profile variable."""

    match identifier:
        case None | "":
            return Missing()
        case str():
            pass
        case _:
            return Missing(NotAString(identifier, type(identifier).__name__, source))

    resolved = _resolve_alias(identifier, env)
    name = _claiming_name(resolved, frozenset(models))
    if name is None:
        return Unclaimed(resolved, source)
    return Claimed(name, resolved, source)


def _alias_of(profile_variable: str) -> str:
    return profile_variable.removeprefix(PROFILE_VARIABLE_PREFIX).removesuffix("_MODEL").lower()


def _resolve_alias(identifier: str, env: Mapping[str, str]) -> str:
    """The text of the profile variable an alias names, or the identifier where none is set."""

    for variable in PROFILE_VARIABLES:
        if identifier == _alias_of(variable):
            return env.get(variable) or identifier
    return identifier


def _claiming_name(identifier: str, names: frozenset[str]) -> str | None:
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
