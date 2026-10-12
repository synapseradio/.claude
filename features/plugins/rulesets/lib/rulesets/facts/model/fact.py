"""The model fact a resolution reaches: claimed, unclaimed, or missing, with its source."""

from dataclasses import dataclass
from typing import Literal

from rulesets.notices import Notice

type SessionVariable = Literal["ANTHROPIC_MODEL", "ANTHROPIC_DEFAULT_MODEL"]
type ForceLever = Literal[
    "CLAUDE_CODE_SUBAGENT_MODEL_FORCE", "CLAUDE_CODE_COORDINATOR_FORCE_WORKER_INHERIT_MODEL"
]


@dataclass(frozen=True)
class FromVariable:
    """A session identifier that `name` held, with the value it held."""

    name: SessionVariable
    value: str


@dataclass(frozen=True)
class FromForceLever:
    """A delegate identifier that a force lever decided."""

    lever: ForceLever


type ModelSource = (
    Literal[
        "harness-reported",
        "session-record",
        "no-identifier",
        "switch-target",
        "per-spawn",
        "definition-pin",
        "built-in-pin",
        "subagent-default-variable",
        "parent-record",
    ]
    | FromVariable
    | FromForceLever
)


@dataclass(frozen=True)
class Claimed:
    """An identifier that the declared name `name` claims."""

    name: str
    identifier: str
    source: ModelSource


@dataclass(frozen=True)
class Unclaimed:
    """A string identifier that no declared name claims."""

    identifier: str
    source: ModelSource


@dataclass(frozen=True)
class NotAString:
    """An identifier a source reported that is not a string, with its value and type."""

    value: object
    type_name: str
    source: ModelSource


@dataclass(frozen=True)
class Missing:
    """No string identifier, either because no source named one or because `not_a_string` did."""

    not_a_string: NotAString | None = None

    @property
    def source(self) -> ModelSource:
        return self.not_a_string.source if self.not_a_string else "no-identifier"


type ModelFact = Claimed | Unclaimed | Missing


@dataclass(frozen=True)
class ModelResolution:
    """The model fact one resolution reached, and the notices it raised on the way."""

    fact: ModelFact
    notices: tuple[Notice, ...] = ()


def claimed_name(fact: ModelFact) -> str | None:
    """The value of `Facts.model` for a model fact."""

    match fact:
        case Claimed(name=name):
            return name
        case Unclaimed() | Missing():
            return None
