"""A hook payload parsed into the request a delivery answers."""

from __future__ import annotations

import dataclasses
from collections.abc import Mapping

FORK = "fork"


@dataclasses.dataclass(frozen=True)
class SessionStart:
    """The main session starting, resuming, clearing, or compacting."""

    session_id: str
    payload: Mapping[str, object]

    event = "SessionStart"

    @property
    def agent(self) -> str | None:
        """The agent the session launched under with `--agent`, if any."""

        return _text(self.payload.get("agent_type"))

    @property
    def source(self) -> str | None:
        """What started the session: `startup`, `resume`, `clear`, or `compact`."""

        return _text(self.payload.get("source"))


@dataclasses.dataclass(frozen=True)
class ModelSwitch:
    """The main session's model changing to `to_model` from `from_model`, when the harness names it.

    `agent` is the agent the session launched under, which a switch payload does not carry.
    """

    session_id: str
    from_model: str | None
    to_model: str
    prompt_id: str | None
    payload: Mapping[str, object]
    agent: str | None = None

    event = "PostModelSwitch"

    def origin(self) -> ModelSwitch:
        """The switch read as if the session had stayed on `from_model`; absent where none is named."""

        return dataclasses.replace(self, to_model=self.from_model) if self.from_model else self


@dataclasses.dataclass(frozen=True)
class SubagentStart:
    """A delegate starting."""

    session_id: str
    agent_id: str | None
    agent_type: str | None
    payload: Mapping[str, object]

    event = "SubagentStart"


@dataclasses.dataclass(frozen=True)
class Forked:
    """A forked session or a fork subagent starting; its conversation already holds the rules."""


@dataclasses.dataclass(frozen=True)
class SessionEnd:
    """The main session ending."""

    session_id: str

    event = "SessionEnd"


@dataclasses.dataclass(frozen=True)
class Unreadable:
    """A payload that is no request: why, and the session and event it still names."""

    reason: str
    session_id: str | None = None
    event: str | None = None


type DeliveryStart = SessionStart | ModelSwitch | SubagentStart
type DeliveryRequest = DeliveryStart | Unreadable
type HookRequest = DeliveryRequest | SessionEnd | Forked


def parse_request(payload: object) -> HookRequest:
    """The request a hook payload makes, or why the payload is no request."""

    if not isinstance(payload, dict):
        return Unreadable("the payload is not a JSON object")
    session_id = _text(payload.get("session_id"))
    event_name = _text(payload.get("hook_event_name"))
    if _is_fork(event_name, payload):
        return Forked()
    if session_id is None:
        return Unreadable("the payload names no session", event=event_name)
    match event_name:
        case "SessionStart":
            return SessionStart(session_id, payload)
        case "SubagentStart":
            agent_type = _text(payload.get("agent_type"))
            agent_id = _text(payload.get("agent_id"))
            return SubagentStart(session_id, agent_id, agent_type, payload)
        case "PostModelSwitch":
            to_model = _text(payload.get("to_model"))
            if to_model is None:
                return Unreadable("the switch names no target model", session_id, event_name)
            return ModelSwitch(
                session_id,
                _text(payload.get("from_model")),
                to_model,
                _text(payload.get("prompt_id")),
                payload,
            )
        case "SessionEnd":
            return SessionEnd(session_id)
        case event:
            return Unreadable(f"no delivery answers the event {event!r}", session_id, event)


def _is_fork(event_name: str | None, payload: dict) -> bool:
    match event_name:
        case "SessionStart":
            return _text(payload.get("source")) == FORK
        case "SubagentStart":
            return _text(payload.get("agent_type")) == FORK
        case _:
            return False


def _text(value: object) -> str | None:
    return value if isinstance(value, str) and value else None
