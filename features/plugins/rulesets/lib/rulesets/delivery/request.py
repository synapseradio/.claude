"""A hook payload parsed into the request a delivery answers."""

from __future__ import annotations

import dataclasses
from collections.abc import Mapping

FORK_AGENT_TYPE = "fork"


@dataclasses.dataclass(frozen=True)
class SessionStart:
    """The main session starting, resuming, clearing, forking, or compacting."""

    session_id: str
    payload: Mapping[str, object]

    event = "SessionStart"

    @property
    def agent(self) -> str | None:
        """The agent the session launched under with `--agent`, if any."""

        return _text(self.payload.get("agent_type"))


@dataclasses.dataclass(frozen=True)
class SubagentStart:
    """A delegate starting."""

    session_id: str
    agent_id: str | None
    agent_type: str | None
    payload: Mapping[str, object]

    event = "SubagentStart"


@dataclasses.dataclass(frozen=True)
class ForkStart:
    """A fork subagent starting; it inherits its parent's conversation."""

    session_id: str
    agent_id: str | None

    event = "SubagentStart"


@dataclasses.dataclass(frozen=True)
class Unreadable:
    reason: str


type DeliveryRequest = SessionStart | SubagentStart | ForkStart | Unreadable


def parse_request(payload: object) -> DeliveryRequest:
    """The request a hook payload makes, or why the payload is no request."""

    if not isinstance(payload, dict):
        return Unreadable("the payload is not a JSON object")
    session_id = _text(payload.get("session_id"))
    if session_id is None:
        return Unreadable("the payload names no session")
    match payload.get("hook_event_name"):
        case "SessionStart":
            return SessionStart(session_id, payload)
        case "SubagentStart":
            agent_type = _text(payload.get("agent_type"))
            agent_id = _text(payload.get("agent_id"))
            if agent_type == FORK_AGENT_TYPE:
                return ForkStart(session_id, agent_id)
            return SubagentStart(session_id, agent_id, agent_type, payload)
        case event:
            return Unreadable(f"no delivery answers the event {event!r}")


def _text(value: object) -> str | None:
    return value if isinstance(value, str) and value else None
