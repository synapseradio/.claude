"""The contexts a comparison covers: each model identifier crossed with each agent and with none."""

from __future__ import annotations

import dataclasses
from collections.abc import Iterable

from rulesets.adopt.agent_exclusions import AgentDefinition


@dataclasses.dataclass(frozen=True)
class ContextKey:
    """A context by its model identifier (None: no model) and its agent (None: no agent)."""

    identifier: str | None
    agent: str | None

    def __str__(self) -> str:
        model = f"model {self.identifier}" if self.identifier else "no model"
        return f"{model}, {f'agent {self.agent}' if self.agent else 'no agent'}"


def matrix(
    identifiers: Iterable[str | None], definitions: Iterable[AgentDefinition]
) -> tuple[ContextKey, ...]:
    """Each distinct identifier with no agent first, then with each definition's agent by name."""

    agents = (None, *sorted({definition.name for definition in definitions}))
    return tuple(
        ContextKey(identifier, agent)
        for identifier in dict.fromkeys(identifiers)
        for agent in agents
    )
