"""The shape of one delivery's record."""

from __future__ import annotations

import dataclasses
import hashlib
from typing import Literal

from rulesets.delivery.parts import Body
from rulesets.notices import SHOWN, Notice


@dataclasses.dataclass(frozen=True)
class RuleLine:
    """A rule delivered, with the SHA-256 digest of its body."""

    rule: str
    variant: str | None
    digest: str


@dataclasses.dataclass(frozen=True)
class WithheldLine:
    rule: str
    error: str


@dataclasses.dataclass(frozen=True)
class ReportedValue:
    """A non-string value a source reported as the model identifier, and its type."""

    value: object
    type: str


@dataclasses.dataclass(frozen=True)
class ModelLine:
    """The model fact: its declared name and identifier where claimed, with the source.

    `not_a_string` is set where the source named a value that is not a string.
    """

    state: Literal["claimed", "unclaimed", "missing"]
    name: str | None
    identifier: str | None
    source: str
    not_a_string: ReportedValue | None = None


@dataclasses.dataclass(frozen=True)
class ToolsLine:
    """The tools fact and the definition file it came from.

    `tools` holds the tools a definition lists, or the tools it removes where `state` is `all-but`.
    """

    state: Literal["listed", "all-but", "absent"]
    tools: tuple[str, ...]
    source: str | None


@dataclasses.dataclass(frozen=True)
class FlagLine:
    """A flag the context held, with where it came from."""

    name: str
    source: Literal["launch", "toggle"]


@dataclasses.dataclass(frozen=True)
class DeliveryRecord:
    """What one delivery composed and sent. `message_sent` says whether the person was shown a message."""

    session_id: str
    agent_id: str | None
    scope: Literal["session", "delegate"]
    kind: str
    agent: str | None
    model: ModelLine | None
    tools: ToolsLine | None
    flags: tuple[FlagLine, ...]
    rules: tuple[RuleLine, ...]
    withheld: tuple[WithheldLine, ...]
    left_out: tuple[str, ...]
    notices: tuple[Notice, ...]
    message_sent: bool

    def to_json(self) -> dict[str, object]:
        document = dataclasses.asdict(self)
        document["notices"] = [
            {"kind": n.kind, "subject": n.subject, "shown": n.kind in SHOWN} for n in self.notices
        ]
        return document


def digest_of(body: Body) -> str:
    return hashlib.sha256(body.text.encode("utf-8")).hexdigest()
