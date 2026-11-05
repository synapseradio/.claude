"""A later part of a delivery: part k of the plan the first part wrote, and nothing composed."""

from __future__ import annotations

import pathlib
import time

from rulesets.audit import log
from rulesets.audit.delivery_record import digest_of_text
from rulesets.audit.emitted_record import EmittedRecord
from rulesets.delivery.hook_output import PartOutput
from rulesets.delivery.plan import Delivering, await_plan
from rulesets.delivery.request import ModelSwitch, SessionStart, SubagentStart
from rulesets.locations import Locations


def deliver_later(
    request: SessionStart | ModelSwitch | SubagentStart,
    locations: Locations,
    slot: pathlib.Path,
    part: int,
) -> PartOutput:
    """The text of part `part`, which is recorded as emitted, or nothing where the plan has no such part."""

    plan = await_plan(slot, part)
    if not isinstance(plan, Delivering):
        return PartOutput()
    for planned in plan.parts:
        if planned.index == part:
            text = planned.text
            record = EmittedRecord(
                session_id=request.session_id,
                agent_id=request.agent_id if isinstance(request, SubagentStart) else None,
                time_ns=time.time_ns(),
                part=part,
                part_count=len(plan.parts),
                model=plan.model,
                rules=tuple(body.rule for body in planned.bodies),
                digest=digest_of_text(text),
            )
            log.append(log.emitted_file(locations, request.session_id, part), record.to_json())
            return PartOutput(text)
    return PartOutput()
