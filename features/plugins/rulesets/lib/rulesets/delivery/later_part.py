"""A later part of a delivery: part k of the plan the first part wrote, and nothing composed."""

from __future__ import annotations

import pathlib

from rulesets.delivery.hook_output import PartOutput
from rulesets.delivery.plan import await_plan


def deliver_later(slot: pathlib.Path, part: int) -> PartOutput:
    """The text of part `part`, or nothing where the plan has no such part or no plan was written."""

    plan = await_plan(slot, part)
    if plan is None:
        return PartOutput()
    for planned in plan.parts:
        if planned.index == part:
            return PartOutput("".join(body.text for body in planned.bodies))
    return PartOutput()
