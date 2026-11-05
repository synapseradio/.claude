"""A payload that is no request, turned into a stderr line, a record, and where the event shows one, a notice."""

from __future__ import annotations

import sys

from rulesets.audit.delivery_record import RecordKind, Scope
from rulesets.delivery.failure import append_failed, failed_record
from rulesets.delivery.hook_output import MESSAGE_SHOWN, PartOutput, hook_output
from rulesets.delivery.request import Unreadable
from rulesets.locations import Locations
from rulesets.notices import Notice

_RECORDED: dict[str, tuple[Scope, RecordKind]] = {
    "SessionStart": ("session", "session"),
    "PostModelSwitch": ("switch", "session"),
    "SubagentStart": ("delegate", "delegate"),
}


def report_unreadable(request: Unreadable, locations: Locations) -> str:
    """The hook output for a payload no delivery can answer; stderr always carries the reason.

    A payload that names its session also leaves a record carrying the reason, and where the
    event shows the person a message, the output is that message.
    """

    print(f"deliver.py: no delivery ({request.reason})", file=sys.stderr)
    notice = Notice("delivery-failure", f"delivery failed ({request.reason})")
    shown = MESSAGE_SHOWN.get(request.event or "", False)
    if request.session_id is not None and request.event in _RECORDED:
        scope, kind = _RECORDED[request.event]
        append_failed(
            locations,
            failed_record(
                session_id=request.session_id,
                agent_id=None,
                scope=scope,
                kind=kind,
                notice=notice,
                message_sent=shown,
                switch=None,
            ),
        )
    if shown and request.event is not None:
        return hook_output(request.event, PartOutput(message=notice.subject))
    return ""
