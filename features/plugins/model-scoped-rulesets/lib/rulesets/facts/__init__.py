"""The facts a context's conditions can test."""

from dataclasses import dataclass
from typing import Literal

type Kind = Literal["session", "delegate", "fork"]


@dataclass(frozen=True)
class Facts:
    """What a `when` item's condition can test in one context.

    `model` is the declared name that claimed the context's model identifier, and
    None where the identifier is unclaimed or missing, so every `model` test is
    false there. `agent` is None where the context carries no agent fact.
    """

    model: str | None
    agent: str | None
    kind: Kind
    flags: frozenset[str]
