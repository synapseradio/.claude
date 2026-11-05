"""The plan the first part writes and every later part reads, once, in the delivery that wrote it."""

from __future__ import annotations

import dataclasses
import json
import pathlib
import time
import uuid

from rulesets import ordering
from rulesets.audit.delivery_record import ModelLine
from rulesets.delivery.parts import Body, Part

PLAN_FILE = "plan.json"


@dataclasses.dataclass(frozen=True)
class Delivering:
    """The parts of one delivery, and the model fact each later part records beside them."""

    generation: str
    parts: tuple[Part, ...]
    model: ModelLine


@dataclasses.dataclass(frozen=True)
class Silent:
    """A delivery whose later parts send nothing: a fork, a switch that changes no rule, a failure."""

    generation: str


type Plan = Delivering | Silent


def new_generation() -> str:
    """The name of one delivery, made by its first part."""

    return uuid.uuid4().hex


def write_plan(slot: pathlib.Path, plan: Plan) -> None:
    """Write the plan in one atomic replace."""

    match plan:
        case Silent(generation):
            document: dict[str, object] = {"generation": generation}
        case Delivering(generation, parts, model):
            document = {
                "generation": generation,
                "model": dataclasses.asdict(model),
                "parts": [
                    {
                        "index": part.index,
                        "bodies": [{"rule": b.rule, "text": b.text} for b in part.bodies],
                    }
                    for part in parts
                ],
            }
    temporary = slot / f"{PLAN_FILE}.tmp"
    temporary.write_text(json.dumps(document), encoding="utf-8")
    temporary.replace(slot / PLAN_FILE)


def await_plan(slot: pathlib.Path, part: int) -> Plan | None:
    """The plan of the delivery this part belongs to, once the part before it has exited.

    A part takes each plan once: it waits past the plan it last took, so an identical payload
    delivered again meets the new delivery's plan and never the earlier one. None where no
    new plan appeared before the deadline. The plan is read again once the part before has
    exited, so a failure of the first part reaches every later part as a silent plan.
    """

    plan = _fresh_plan(slot, part)
    if plan is None:
        return None
    _mark_taken(slot, part, plan.generation)
    ordering.hold(slot, plan.generation, part)
    ordering.wait_for_predecessor(slot, plan.generation, part)
    settled = _read_plan(slot)
    return settled if settled is not None and settled.generation == plan.generation else None


def _fresh_plan(slot: pathlib.Path, part: int) -> Plan | None:
    start = time.monotonic()
    while True:
        plan = _read_plan(slot)
        if plan is not None and plan.generation != _last_taken(slot, part):
            return plan
        if time.monotonic() - start >= ordering.ORDER_DEADLINE:
            return None
        time.sleep(ordering.STARTUP_POLL)


def _taken_file(slot: pathlib.Path, part: int) -> pathlib.Path:
    return slot / f"taken-{part}"


def _last_taken(slot: pathlib.Path, part: int) -> str | None:
    try:
        return _taken_file(slot, part).read_text(encoding="utf-8")
    except OSError:
        return None


def _mark_taken(slot: pathlib.Path, part: int, generation: str) -> None:
    _taken_file(slot, part).write_text(generation, encoding="utf-8")


def _read_plan(slot: pathlib.Path) -> Plan | None:
    try:
        document = json.loads((slot / PLAN_FILE).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    generation = document["generation"]
    if "parts" not in document:
        return Silent(generation)
    return Delivering(
        generation,
        tuple(
            Part(entry["index"], tuple(Body(b["rule"], b["text"]) for b in entry["bodies"]))
            for entry in document["parts"]
        ),
        ModelLine.from_json(document["model"]),
    )
