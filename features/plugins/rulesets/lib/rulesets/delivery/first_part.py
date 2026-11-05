"""The first part of a delivery: resolve facts, compose, plan, record, and emit part 1."""

from __future__ import annotations

import json
import pathlib
from collections.abc import Mapping

from rulesets.audit import log
from rulesets.audit.delivery_record import (
    DeliveryRecord,
    FlagLine,
    ModelLine,
    ReportedValue,
    RuleLine,
    SwitchLine,
    ToolsLine,
    WithheldLine,
    digest_of,
)
from rulesets.compose.composition import Composition, compose
from rulesets.delivery.hook_output import MESSAGE_SHOWN, PartOutput
from rulesets.delivery.parts import MAX_PARTS, pack_parts
from rulesets.delivery.plan import Plan, write_plan
from rulesets.delivery.request import ForkStart, ModelSwitch, SessionStart, SubagentStart
from rulesets.delivery.rule_bodies import bodies_of
from rulesets.facts.context import AllToolsBut, Facts, ListedTools
from rulesets.facts.model.delegate import resolve_fork_model
from rulesets.facts.model.fact import (
    Claimed,
    FromForceLever,
    FromVariable,
    Missing,
    ModelFact,
    Unclaimed,
)
from rulesets.facts.model.record import write_model_record
from rulesets.facts.resolve_context import resolve_context
from rulesets.locations import Locations
from rulesets.notices import (
    SHOWN,
    Notice,
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
from rulesets.session.state import SessionState, read_state
from rulesets.source.directory import (
    Missing as ManifestMissing,
)
from rulesets.source.directory import (
    Present,
    RulesetsDirectory,
    Unparsable,
    read_directory,
)
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

    match request:
        case ForkStart():
            return _deliver_fork(request, locations, slot)
        case SessionStart() | ModelSwitch():
            state, scope = SessionState(), "session"
        case SubagentStart():
            state, scope = read_state(locations, request.session_id), "delegate"

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
    write_plan(slot, Plan(parts))

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
    log.append(
        log.session_dir(locations, request.session_id) / log.DELIVERIES_FILE,
        DeliveryRecord(
            session_id=request.session_id,
            agent_id=request.agent_id if isinstance(request, SubagentStart) else None,
            scope=scope,
            kind=resolved.facts.kind,
            agent=resolved.facts.agent if isinstance(resolved.facts.agent, str) else None,
            model=_model_line(resolved.model),
            tools=_tools_line(resolved.facts, resolved.tools_source),
            flags=tuple(FlagLine(f.name, f.source.value) for f in resolved.flags),
            rules=tuple(RuleLine(r.rule, r.variant, digests[r.rule]) for r in composition.rules),
            withheld=tuple(WithheldLine(w.rule, w.error) for w in composition.withheld),
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

    write_plan(slot, Plan(()))
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
            agent=None,
            model=_model_line(fact),
            tools=None,
            flags=(),
            rules=(),
            withheld=(),
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


def _model_line(fact: ModelFact) -> ModelLine:
    match fact:
        case Claimed(name, identifier, source):
            return ModelLine("claimed", name, identifier, _label(source))
        case Unclaimed(identifier, source):
            return ModelLine("unclaimed", None, identifier, _label(source))
        case Missing(not_a_string=None):
            return ModelLine("missing", None, None, _label(fact.source))
        case Missing(not_a_string=reported):
            value = json.loads(json.dumps(reported.value, default=str))
            return ModelLine(
                "missing",
                None,
                None,
                _label(fact.source),
                ReportedValue(value, reported.type_name),
            )


def _tools_line(facts: Facts, source: pathlib.Path | None) -> ToolsLine:
    path = None if source is None else str(source)
    match facts.tools:
        case ListedTools(tools=tools):
            return ToolsLine("listed", tuple(sorted(tools)), path)
        case AllToolsBut(removed=removed):
            return ToolsLine("all-but", tuple(sorted(removed)), path)
        case _:
            return ToolsLine("absent", (), None)


def _label(source: object) -> str:
    match source:
        case FromVariable(name=name, value=value):
            return f"{name}={value}"
        case FromForceLever(lever=lever):
            return lever.value
        case _:
            return str(source)
