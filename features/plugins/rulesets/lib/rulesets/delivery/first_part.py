"""The first part of a delivery: resolve facts, compose, plan, record, and emit part 1."""

from __future__ import annotations

import pathlib
import time
from collections.abc import Mapping

from rulesets.audit import log
from rulesets.audit.delivery_record import (
    AbsentLine,
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
from rulesets.compose.composition import Composition, compose
from rulesets.delivery.hook_output import MESSAGE_SHOWN, PartOutput
from rulesets.delivery.parts import MAX_PARTS, pack_parts
from rulesets.delivery.plan import Plan, clear_plan, write_plan
from rulesets.delivery.request import ForkStart, ModelSwitch, SessionStart, SubagentStart
from rulesets.delivery.rule_bodies import bodies_of
from rulesets.facts.context import Absent, Facts
from rulesets.facts.model.delegate import resolve_fork_model
from rulesets.facts.model.fact import Claimed, Missing, ModelFact, Unclaimed
from rulesets.facts.model.record import write_model_record
from rulesets.facts.resolve_context import resolve_context
from rulesets.locations import Locations
from rulesets.notices import (
    SHOWN,
    Notice,
    absent_agent_notice,
    absent_tools_notice,
    block_skipped_notice,
    fork_notice,
    left_out_notice,
    manifest_missing_notice,
    manifest_unparsable_notice,
    nothing_received_notice,
    reference_notice,
    scaffold_failed_notice,
    scaffolded_notice,
    variant_conflict_notice,
    withheld_notice,
)
from rulesets.session.state import SessionState, read_state, state_path
from rulesets.source.directory import (
    Missing as ManifestMissing,
)
from rulesets.source.directory import (
    Present,
    RulesetsDirectory,
    Unparsable,
    read_directory,
)
from rulesets.source.manifest import MANIFEST_FILE
from rulesets.source.scaffold import (
    AlreadyPresent,
    Scaffolded,
    ScaffoldFailed,
    scaffold,
)


def deliver_first(
    request: SessionStart | ModelSwitch | SubagentStart | ForkStart,
    locations: Locations,
    environ: Mapping[str, str],
    slot: pathlib.Path,
    prior_notices: tuple[Notice, ...] = (),
) -> PartOutput:
    """Compose the context's rules once, write the plan, append the record, and emit part 1.

    `prior_notices` are the notices the session's start or switch already drew.
    """

    scope: Scope
    match request:
        case ForkStart():
            return _deliver_fork(request, locations, slot)
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
    write_plan(slot, Plan(parts, model))

    notices = (
        *prior_notices,
        *_directory_notices(scaffolded, directory, locations.rulesets),
        *resolved.notices,
        *_composition_notices(composition),
        *(left_out_notice(rule) for rule in left_out),
        *((nothing_received_notice(),) if not parts else ()),
    )
    message = _message(request.event, notices)
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
    first = "".join(body.text for body in parts[0].bodies) if parts else None
    return PartOutput(first, message)


def _switch_line(request: SessionStart | ModelSwitch | SubagentStart) -> SwitchLine | None:
    if isinstance(request, ModelSwitch):
        return SwitchLine(request.from_model, request.to_model, request.prompt_id)
    return None


def _deliver_fork(request: ForkStart, locations: Locations, slot: pathlib.Path) -> PartOutput:
    """A fork inherits its parent's rules, so it receives none; its record names why and the parent's model."""

    clear_plan(slot)
    directory = read_directory(locations.rulesets)
    models = directory.manifest.manifest.models if isinstance(directory.manifest, Present) else ()
    fact = resolve_fork_model(request.session_id, models, locations.state)
    log.append(
        log.session_dir(locations, request.session_id) / log.DELIVERIES_FILE,
        DeliveryRecord(
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
        ).to_json(),
    )
    return PartOutput()


def _directory_notices(
    scaffolded: Scaffolded | AlreadyPresent | ScaffoldFailed,
    directory: RulesetsDirectory,
    root: pathlib.Path,
) -> tuple[Notice, ...]:
    """What the directory's state says: a scaffold's outcome, or why a manifest is not read."""

    match scaffolded:
        case Scaffolded():
            return (scaffolded_notice(str(root)),)
        case ScaffoldFailed(reason=reason):
            return (scaffold_failed_notice(str(root), reason),)
        case AlreadyPresent():
            pass
    match directory.manifest:
        case ManifestMissing():
            return (manifest_missing_notice(str(root / "manifest.yaml")),)
        case Unparsable(error=error):
            return (manifest_unparsable_notice(str(error)),)
        case Present():
            return ()


def _identifier_of(fact: ModelFact) -> str | None:
    match fact:
        case Claimed(identifier=identifier) | Unclaimed(identifier=identifier):
            return identifier
        case Missing():
            return None


def _composition_notices(composition: Composition) -> tuple[Notice, ...]:
    return (
        *(block_skipped_notice(b.condition, b.undeclared) for b in composition.skipped_blocks),
        *(reference_notice(s.text, s.line, s.name) for s in composition.skipped),
        *(withheld_notice(w.rule, w.error) for w in composition.withheld),
        *(variant_conflict_notice(c.rule, c.variant) for c in composition.conflicts),
    )


def _message(event: str, notices: tuple[Notice, ...]) -> str | None:
    """The shown notices as one message, or None where none is shown or the event shows none."""

    shown = [notice.subject for notice in notices if notice.kind in SHOWN]
    if not shown or not MESSAGE_SHOWN[event]:
        return None
    return "\n".join(shown)


def _agent_name(facts: Facts) -> str | None:
    return None if isinstance(facts.agent, Absent) else facts.agent
