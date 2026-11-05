"""Session state across clear, fork, and end; compaction and resume leave it as it is."""

from __future__ import annotations

from rulesets.delivery.request import SessionEnd, SessionStart
from rulesets.locations import Locations
from rulesets.session.fork_parent import Parent, fork_parent
from rulesets.session.state import copy_state, remove_state


def on_session_start(request: SessionStart, locations: Locations) -> None:
    """A clear ends the session's state; a fork starts with a copy of its parent's."""

    match request.source:
        case "clear":
            remove_state(locations, request.session_id)
        case "fork" if request.transcript_path is not None:
            match fork_parent(request.transcript_path):
                case Parent(session_id):
                    copy_state(locations, session_id, request.session_id)


def on_session_end(request: SessionEnd, locations: Locations) -> None:
    """The session's state ends with the session."""

    remove_state(locations, request.session_id)
