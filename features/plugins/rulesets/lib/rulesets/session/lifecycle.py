"""Session state across clear, resume, and end; compaction leaves it as it is."""

from __future__ import annotations

from rulesets.delivery.request import SessionEnd, SessionStart
from rulesets.locations import Locations
from rulesets.session.launch_agent import write_launch_agent
from rulesets.session.state import remove_state


def on_session_start(request: SessionStart, locations: Locations) -> None:
    """A clear or a resume ends the session's state.

    A resume ends it because a session that crashed sent no SessionEnd. Every start records
    the agent the session launched under, for the switches that follow.
    """

    write_launch_agent(locations, request.session_id, request.agent)
    match request.source:
        case "clear" | "resume":
            remove_state(locations, request.session_id)


def on_session_end(request: SessionEnd, locations: Locations) -> None:
    """The session's state ends with the session."""

    remove_state(locations, request.session_id)
