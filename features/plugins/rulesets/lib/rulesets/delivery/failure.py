"""A delivery that raises, turned into an empty output, a record, and for the first part a shown notice."""

from __future__ import annotations

import contextlib
import sys
import traceback
from collections.abc import Callable

from rulesets.audit import log
from rulesets.delivery.hook_output import MESSAGE_SHOWN, PartOutput, hook_output
from rulesets.locations import Locations
from rulesets.notices import failure_notice

FAILURES_FILE = "failures.jsonl"


def run_guarded(
    entry: Callable[[], str],
    *,
    event: str,
    session_id: str,
    first_part: bool,
    command: str,
    locations: Locations,
) -> str:
    """The output of `entry`, or where it raises, the output of a failed delivery.

    A failure of the environment, an `OSError`, is named alone. Any other failure is a defect,
    and its traceback goes to stderr. The notice is shown only by the first part, and only on an
    event whose message the person sees. The record is written where the log is writable.
    """

    try:
        return entry()
    except Exception as failure:
        if not isinstance(failure, OSError):
            traceback.print_exc(file=sys.stderr)
        notice = failure_notice(f"{type(failure).__name__}: {failure}", command)
        _record(locations, session_id, event, notice.subject)
        if first_part and MESSAGE_SHOWN.get(event, False):
            return hook_output(event, PartOutput(message=notice.subject))
        return ""


def _record(locations: Locations, session_id: str, event: str, subject: str) -> None:
    with contextlib.suppress(OSError):
        log.append(
            log.session_dir(locations, session_id) / FAILURES_FILE,
            {"event": event, "kind": "delivery-failure", "subject": subject},
        )
