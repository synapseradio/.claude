"""The agent a session launched under, kept for the events whose payload does not name it."""

from __future__ import annotations

import contextlib

from rulesets.locations import Locations


def _path(locations: Locations, session_id: str):
    return locations.state / "agent" / f"{session_id}.txt"


def write_launch_agent(locations: Locations, session_id: str, agent: str | None) -> None:
    """Record the session's agent, or that it launched under none; an unwritable state is left as it is."""

    path = _path(locations, session_id)
    with contextlib.suppress(OSError):
        if agent is None:
            path.unlink(missing_ok=True)
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(agent, encoding="utf-8")


def read_launch_agent(locations: Locations, session_id: str) -> str | None:
    """The agent recorded for the session; None where it launched under none or none was recorded."""

    try:
        return _path(locations, session_id).read_text(encoding="utf-8") or None
    except OSError:
        return None
