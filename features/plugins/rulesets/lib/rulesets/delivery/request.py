"""A hook payload parsed into the request a delivery answers."""

from __future__ import annotations

import dataclasses
import pathlib
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

    @property
    def source(self) -> str | None:
        """What started the session: `startup`, `resume`, `clear`, `compact`, or `fork`."""

        return _text(self.payload.get("source"))

    @property
    def transcript_path(self) -> pathlib.Path | None:
        """Where the harness keeps this session's transcript."""

        path = _text(self.payload.get("transcript_path"))
        return None if path is None else pathlib.Path(path).expanduser()


@dataclasses.dataclass(frozen=True)
class ModelSwitch:
    """The main session's model changing to `to_model` from `from_model`, when the harness names it."""

    session_id: str
    from_model: str | None
    to_model: str
    prompt_id: str | None
    payload: Mapping[str, object]

    event = "PostModelSwitch"

    @property
    def agent(self) -> str | None:
        """The agent the session launched under with `--agent`, if any."""

        return _text(self.payload.get("agent_type"))

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
class ForkStart:
    """A fork subagent starting; it inherits its parent's conversation."""

    session_id: str
    agent_id: str | None

    event = "SubagentStart"


@dataclasses.dataclass(frozen=True)
class SessionEnd:
    """The main session ending."""

    session_id: str

    event = "SessionEnd"


@dataclasses.dataclass(frozen=True)
class Unreadable:
    reason: str


type DeliveryRequest = SessionStart | ModelSwitch | SubagentStart | ForkStart | Unreadable
type HookRequest = DeliveryRequest | SessionEnd


def parse_request(payload: object) -> HookRequest:
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
        case "PostModelSwitch":
            to_model = _text(payload.get("to_model"))
            if to_model is None:
                return Unreadable("the switch names no target model")
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
            return Unreadable(f"no delivery answers the event {event!r}")


def _text(value: object) -> str | None:
    return value if isinstance(value, str) and value else None
