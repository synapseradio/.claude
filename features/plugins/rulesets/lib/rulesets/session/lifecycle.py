"""Session state across clear, fork, and end; compaction and resume leave it as it is."""

from __future__ import annotations

from rulesets.delivery.request import SessionEnd, SessionStart
from rulesets.locations import Locations
from rulesets.notices import Notice, fork_parent_missing_notice
from rulesets.session.fork_parent import Parent, Unknown, fork_parent
from rulesets.session.state import copy_state, remove_state


def on_session_start(request: SessionStart, locations: Locations) -> tuple[Notice, ...]:
    """A clear ends the session's state; a fork starts with a copy of its parent's.

    A fork whose parent is not found starts with empty state, and the notices say so.
    """

    match request.source:
        case "clear":
            remove_state(locations, request.session_id)
        case "fork":
            parent = (
                fork_parent(request.transcript_path)
                if request.transcript_path is not None
                else Unknown()
            )
            match parent:
                case Parent(session_id):
                    copy_state(locations, session_id, request.session_id)
                case Unknown():
                    return (fork_parent_missing_notice(),)
    return ()


def on_session_end(request: SessionEnd, locations: Locations) -> None:
    """The session's state ends with the session."""

    remove_state(locations, request.session_id)
