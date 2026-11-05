"""The first part of a delivery: resolve facts, compose, record, plan, and emit part 1."""

from __future__ import annotations

import pathlib
import time
from collections.abc import Mapping

from rulesets.audit import log
from rulesets.audit.delivery_record import (
    ConflictLine,
    DeliveryRecord,
    FlagLine,
    ModelLine,
    RuleLine,
    Scope,
    SessionStateLine,
    SkippedBlockLine,
    SkippedReferenceLine,
    SwitchLine,
    WithheldLine,
    agent_line,
    digest_of,
    tools_line,
)
from rulesets.compose.composition import compose
from rulesets.delivery.delivery_notices import composition_notices, directory_notices, shown_message
from rulesets.delivery.hook_output import PartOutput
from rulesets.delivery.parts import MAX_PARTS, pack_parts
from rulesets.delivery.plan import Delivering, write_plan
from rulesets.delivery.request import ModelSwitch, SessionStart, SubagentStart
from rulesets.delivery.rule_bodies import bodies_of
from rulesets.facts.context import Absent, Facts
from rulesets.facts.model.fact import Claimed, Missing, ModelFact, Unclaimed
from rulesets.facts.model.record import write_model_record
from rulesets.facts.resolve_context import resolve_context
from rulesets.locations import Locations
from rulesets.notices import (
    Notice,
    absent_agent_notice,
    absent_tools_notice,
    left_out_notice,
    nothing_received_notice,
)
from rulesets.session.state import SessionState, read_state, state_path
from rulesets.source.directory import read_directory
from rulesets.source.manifest import MANIFEST_FILE
from rulesets.source.scaffold import scaffold


def deliver_first(
    request: SessionStart | ModelSwitch | SubagentStart,
    locations: Locations,
    environ: Mapping[str, str],
    slot: pathlib.Path,
    generation: str,
    prior_notices: tuple[Notice, ...] = (),
) -> PartOutput:
    """Compose the context's rules once, append the record, write the plan, and emit part 1.

    `prior_notices` are the notices the session's start or switch already drew. The plan is
    written last, so a delivery that fails earlier leaves no plan for a later part to emit.
    """

    scope: Scope
    match request:
        case SessionStart():
            state, scope, state_read = SessionState(), "session", None
        case ModelSwitch():
            state, scope, state_read = SessionState(), "switch", None
        case SubagentStart():
            state, scope = read_state(locations, request.session_id), "delegate"
            state_read = SessionStateLine.of(state_path(locations, request.session_id), state)

    scaffolded = scaffold(locations.rulesets)
    directory = read_directory(locations.rulesets)
    resolved = resolve_context(request, directory, locations, environ)
    if isinstance(request, SessionStart | ModelSwitch):
        write_model_record(request.session_id, _identifier_of(resolved.model), locations.state)
    composition = compose(directory, resolved.facts, state)
    bodies = bodies_of(composition, directory.pool)
    packed = pack_parts(bodies)
    parts, past_last = packed[:MAX_PARTS], packed[MAX_PARTS:]
    left_out = tuple(body.rule for part in past_last for body in part.bodies)
    model = ModelLine.of(resolved.model)

    notices = (
        *prior_notices,
        *directory_notices(scaffolded, directory, locations.rulesets),
        *resolved.notices,
        *composition_notices(composition),
        *(left_out_notice(rule) for rule in left_out),
        *((nothing_received_notice(),) if not parts else ()),
    )
    message = shown_message(request.event, notices)
    digests = {body.rule: digest_of(body) for body in bodies}
    manifest_file = directory.root / MANIFEST_FILE
    log.append(
        log.session_dir(locations, request.session_id) / log.DELIVERIES_FILE,
        DeliveryRecord(
            session_id=request.session_id,
            agent_id=request.agent_id if isinstance(request, SubagentStart) else None,
            scope=scope,
            kind=resolved.facts.kind,
            time_ns=time.time_ns(),
            agent=agent_line(resolved.facts.agent, absent_agent_notice().subject),
            model=model,
            tools=tools_line(
                resolved.facts,
                resolved.tools_source,
                absent_tools_notice(_agent_name(resolved.facts)).subject,
            ),
            flags=tuple(FlagLine(f.name, f.source.value) for f in resolved.flags),
            session_state=state_read,
            part_count=len(parts),
            rules=tuple(RuleLine(r.rule, r.variant, digests[r.rule]) for r in composition.rules),
            withheld=tuple(WithheldLine(w.rule, w.error) for w in composition.withheld),
            skipped_references=tuple(
                SkippedReferenceLine.of(s, manifest_file) for s in composition.skipped
            ),
            skipped_blocks=tuple(
                SkippedBlockLine.of(b, manifest_file) for b in composition.skipped_blocks
            ),
            conflicts=tuple(ConflictLine.of(c) for c in composition.conflicts),
            left_out=left_out,
            notices=notices,
            message_sent=message is not None,
            switch=_switch_line(request),
        ).to_json(),
    )
    write_plan(slot, Delivering(generation, parts, model))
    first = "".join(body.text for body in parts[0].bodies) if parts else None
    return PartOutput(first, message)


def _switch_line(request: SessionStart | ModelSwitch | SubagentStart) -> SwitchLine | None:
    if isinstance(request, ModelSwitch):
        return SwitchLine(request.from_model, request.to_model, request.prompt_id)
    return None


def _identifier_of(fact: ModelFact) -> str | None:
    match fact:
        case Claimed(identifier=identifier) | Unclaimed(identifier=identifier):
            return identifier
        case Missing():
            return None


def _agent_name(facts: Facts) -> str | None:
    return None if isinstance(facts.agent, Absent) else facts.agent
