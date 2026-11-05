"""A fork subagent's delivery: no rules, because it inherits its parent's, and a record saying so."""

from __future__ import annotations

import pathlib
import time

from rulesets.audit import log
from rulesets.audit.delivery_record import AbsentLine, DeliveryRecord, ModelLine
from rulesets.delivery.hook_output import PartOutput
from rulesets.delivery.plan import Silent, write_plan
from rulesets.delivery.request import ForkStart
from rulesets.facts.model.delegate import resolve_fork_model
from rulesets.facts.model.fact import ModelFact
from rulesets.locations import Locations
from rulesets.notices import fork_notice
from rulesets.source.directory import Present, read_directory


def deliver_fork(
    request: ForkStart, locations: Locations, slot: pathlib.Path, generation: str
) -> PartOutput:
    """A fork inherits its parent's rules, so it receives none; its record names why and the parent's model."""

    write_plan(slot, Silent(generation))
    directory = read_directory(locations.rulesets)
    models = directory.manifest.manifest.models if isinstance(directory.manifest, Present) else ()
    fact = resolve_fork_model(request.session_id, models, locations.state)
    log.append(
        log.session_dir(locations, request.session_id) / log.DELIVERIES_FILE,
        _record(request, fact).to_json(),
    )
    return PartOutput()


def _record(request: ForkStart, fact: ModelFact) -> DeliveryRecord:
    return DeliveryRecord(
        session_id=request.session_id,
        agent_id=request.agent_id,
        scope="delegate",
        kind="fork",
        time_ns=time.time_ns(),
        agent=AbsentLine(fork_notice().subject),
        model=ModelLine.of(fact),
        tools=AbsentLine(fork_notice().subject),
        flags=(),
        session_state=None,
        part_count=0,
        rules=(),
        withheld=(),
        skipped_references=(),
        skipped_blocks=(),
        conflicts=(),
        left_out=(),
        notices=(fork_notice(),),
        message_sent=False,
    )
