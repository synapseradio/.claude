"""A delivery that raises, turned into an empty output, a record, and for the first part a shown notice."""

from __future__ import annotations

import contextlib
import pathlib
import sys
import time
import traceback
from collections.abc import Callable

from rulesets.audit import log
from rulesets.audit.delivery_record import (
    AbsentLine,
    DeliveryRecord,
    ModelLine,
    RecordKind,
    Scope,
    SwitchLine,
)
from rulesets.delivery.hook_output import MESSAGE_SHOWN, PartOutput, hook_output
from rulesets.delivery.request import (
    DeliveryStart,
    ForkStart,
    ModelSwitch,
    SessionEnd,
    SessionStart,
    SubagentStart,
)
from rulesets.delivery.rerun import rerun_command
from rulesets.locations import Locations
from rulesets.notices import SHOWN, Notice, failure_notice

_UNKNOWN = "the delivery failed before this fact was read"


def run_guarded(
    entry: Callable[[], str],
    *,
    request: DeliveryStart | SessionEnd,
    first_part: bool,
    raw_payload: str,
    hooks: pathlib.Path,
    locations: Locations,
) -> str:
    """The output of `entry`, or where it raises, the output of a failed delivery.

    A failure of the environment, an `OSError`, is named alone. Any other failure is a defect,
    and its traceback goes to stderr. The first part of a delivery writes the delivery record
    carrying the failure notice, and shows the notice on an event whose message the person sees.
    Where no record can be written, and for every later part, stderr carries the failure alone.
    """

    try:
        return entry()
    except Exception as failure:
        description = f"{type(failure).__name__}: {failure}"
        if not isinstance(failure, OSError):
            traceback.print_exc(file=sys.stderr)
        if not first_part or isinstance(request, SessionEnd):
            print(f"deliver.py: delivery failed ({description})", file=sys.stderr)
            return ""
        notice = failure_notice(description, rerun_command(raw_payload, locations, hooks))
        shown = MESSAGE_SHOWN.get(request.event, False)
        if not _record(locations, request, notice, shown):
            print(f"deliver.py: delivery failed ({description})", file=sys.stderr)
        return hook_output(request.event, PartOutput(message=notice.subject)) if shown else ""


def _record(
    locations: Locations,
    request: DeliveryStart,
    notice: Notice,
    message_sent: bool,
) -> bool:
    """Append the failed delivery's record; False where the log cannot be written."""

    with contextlib.suppress(OSError):
        log.append(
            log.session_dir(locations, request.session_id) / log.DELIVERIES_FILE,
            _failed_record(request, notice, message_sent).to_json(),
        )
        return True
    return False


def _failed_record(
    request: DeliveryStart,
    notice: Notice,
    message_sent: bool,
) -> DeliveryRecord:
    scope: Scope
    kind: RecordKind
    match request:
        case SessionStart():
            scope, kind = "session", "session"
        case ModelSwitch():
            scope, kind = "switch", "session"
        case SubagentStart():
            scope, kind = "delegate", "delegate"
        case ForkStart():
            scope, kind = "delegate", "fork"
    return DeliveryRecord(
        session_id=request.session_id,
        agent_id=request.agent_id if isinstance(request, SubagentStart | ForkStart) else None,
        scope=scope,
        kind=kind,
        time_ns=time.time_ns(),
        agent=AbsentLine(_UNKNOWN),
        model=ModelLine("missing", None, None, _UNKNOWN),
        tools=AbsentLine(_UNKNOWN),
        flags=(),
        session_state=None,
        part_count=0,
        rules=(),
        withheld=(),
        skipped_references=(),
        skipped_blocks=(),
        conflicts=(),
        left_out=(),
        notices=(notice,),
        message_sent=message_sent and notice.kind in SHOWN,
        switch=SwitchLine(request.from_model, request.to_model, request.prompt_id)
        if isinstance(request, ModelSwitch)
        else None,
    )
