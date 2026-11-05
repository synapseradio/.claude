"""A delegate's first delivery kept by `agent_id`, so a resumed delegate receives the same text again."""

from __future__ import annotations

import hashlib
import json
import pathlib

from rulesets.audit import log
from rulesets.delivery.hook_output import PartOutput
from rulesets.delivery.plan import Delivering, plan_document, plan_of, write_plan
from rulesets.delivery.request import SubagentStart
from rulesets.locations import Locations


def store_delivery(locations: Locations, request: SubagentStart, plan: Delivering) -> None:
    """Keep the plan a delegate's first delivery composed; a delegate without an `agent_id` keeps none."""

    path = _path(locations, request)
    if path is not None:
        path.write_text(json.dumps(plan_document(plan)), encoding="utf-8")


def deliver_replay(
    request: SubagentStart, locations: Locations, slot: pathlib.Path, generation: str
) -> PartOutput | None:
    """Part 1 of the stored delivery with its later parts planned, or None where none is stored.

    A replay composes nothing and writes no record, for it repeats the delivery whose record
    stands. The harness re-injects a delegate's context after auto-compaction, and the same
    text is the copy it holds.
    """

    path = _path(locations, request)
    if path is None or not path.is_file():
        return None
    try:
        stored = plan_of(json.loads(path.read_text(encoding="utf-8")))
    except OSError, json.JSONDecodeError, KeyError:
        return None
    if not isinstance(stored, Delivering):
        return None
    write_plan(slot, Delivering(generation, stored.parts, stored.model))
    first = "".join(body.text for body in stored.parts[0].bodies) if stored.parts else None
    return PartOutput(first)


def _path(locations: Locations, request: SubagentStart) -> pathlib.Path | None:
    if request.agent_id is None:
        return None
    return (
        log.session_dir(locations, request.session_id)
        / f"delivery-{hashlib.sha256(request.agent_id.encode()).hexdigest()}.json"
    )
