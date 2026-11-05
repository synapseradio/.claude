"""The plan the first part writes and every later part reads."""

from __future__ import annotations

import dataclasses
import json
import pathlib

from rulesets import ordering
from rulesets.audit.delivery_record import ModelLine
from rulesets.delivery.parts import Body, Part

PLAN_FILE = "plan.json"


@dataclasses.dataclass(frozen=True)
class Plan:
    """The parts of one delivery, and the model fact each later part records beside them."""

    parts: tuple[Part, ...]
    model: ModelLine


def write_plan(slot: pathlib.Path, plan: Plan) -> None:
    """Write the plan in one atomic replace."""

    document = {
        "model": dataclasses.asdict(plan.model),
        "parts": [
            {"index": part.index, "bodies": [{"rule": b.rule, "text": b.text} for b in part.bodies]}
            for part in plan.parts
        ],
    }
    temporary = slot / f"{PLAN_FILE}.tmp"
    temporary.write_text(json.dumps(document), encoding="utf-8")
    temporary.replace(slot / PLAN_FILE)


def clear_plan(slot: pathlib.Path) -> None:
    """Replace the plan with one that delivers nothing, so a later part emits nothing stale."""

    temporary = slot / f"{PLAN_FILE}.tmp"
    temporary.write_text(json.dumps({"parts": []}), encoding="utf-8")
    temporary.replace(slot / PLAN_FILE)


def await_plan(slot: pathlib.Path, part: int) -> Plan | None:
    """The plan part 1 wrote, once the part before this one has exited; None where there is none."""

    ordering.wait_for_predecessor(slot, part)
    try:
        document = json.loads((slot / PLAN_FILE).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if "model" not in document:
        return None
    return Plan(
        tuple(
            Part(entry["index"], tuple(Body(b["rule"], b["text"]) for b in entry["bodies"]))
            for entry in document["parts"]
        ),
        ModelLine.from_json(document["model"]),
    )
