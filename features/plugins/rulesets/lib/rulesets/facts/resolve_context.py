"""A delivery request turned into the facts of its context."""

from __future__ import annotations

import dataclasses
import pathlib
from collections.abc import Mapping

from rulesets.delivery.request import ModelSwitch, SessionStart, SubagentStart
from rulesets.facts.absence_notices import absent_fact_notices
from rulesets.facts.agent_definition import Definition, find_definition
from rulesets.facts.agent_fact import agent_fact
from rulesets.facts.context import ABSENT, UNCLAIMED, Absent, Facts, NoClaim
from rulesets.facts.flags import FlagFact, delegate_flags, launch_flags, session_flags
from rulesets.facts.model.delegate import resolve_delegate_model
from rulesets.facts.model.fact import Claimed, Missing, ModelFact, Unclaimed
from rulesets.facts.model.notice import model_notice
from rulesets.facts.model.session import resolve_session_model, resolve_switch_model
from rulesets.facts.tools_fact import tools_fact
from rulesets.locations import Locations
from rulesets.notices import Notice, flag_notice
from rulesets.session.state import read_state
from rulesets.source.directory import Present, RulesetsDirectory


@dataclasses.dataclass(frozen=True)
class ResolvedContext:
    """The facts a context is composed from, the model fact and flags behind them, and the notices raised."""

    facts: Facts
    model: ModelFact
    notices: tuple[Notice, ...]
    flags: tuple[FlagFact, ...]
    tools_source: pathlib.Path | None


def resolve_context(
    request: SessionStart | ModelSwitch | SubagentStart,
    directory: RulesetsDirectory,
    locations: Locations,
    environ: Mapping[str, str],
) -> ResolvedContext:
    """Resolve the model, agent, kind, and flags of the context a request starts."""

    manifest = directory.manifest.manifest if isinstance(directory.manifest, Present) else None
    models = manifest.models if manifest else ()
    launched = launch_flags(environ, manifest.flags if manifest else ())
    match request:
        case SessionStart():
            resolution = resolve_session_model(request.payload, models, environ, locations.state)
            kind = "session"
            flags = session_flags(launched)
        case ModelSwitch():
            resolution = resolve_switch_model({"to_model": request.to_model}, models)
            kind = "session"
            flags = session_flags(launched)
        case SubagentStart():
            resolution = resolve_delegate_model(
                request.payload, models, environ, locations.state, locations.config
            )
            kind = "delegate"
            flags = delegate_flags(launched, read_state(locations, request.session_id))
    notices = [*resolution.notices]
    if (notice := model_notice(resolution.fact)) is not None:
        notices.append(notice)
    notices.extend(flag_notice(name) for name in launched.undeclared)
    agent = agent_fact(request)
    definition = _definition_of(agent, request, locations)
    tools = tools_fact(definition.front if definition else None)
    notices.extend(absent_fact_notices(manifest, agent, tools))
    facts = Facts(
        _model_in_facts(resolution.fact),
        agent,
        kind,
        frozenset(flag.name for flag in flags),
        request.session_id,
        tools,
    )
    return ResolvedContext(
        facts, resolution.fact, tuple(notices), flags, definition.path if definition else None
    )


def _model_in_facts(fact: ModelFact) -> str | NoClaim | Absent:
    match fact:
        case Claimed(name=name):
            return name
        case Unclaimed():
            return UNCLAIMED
        case Missing():
            return ABSENT


def _definition_of(
    agent: str | Absent,
    request: SessionStart | ModelSwitch | SubagentStart,
    locations: Locations,
) -> Definition | None:
    if isinstance(agent, Absent):
        return None
    cwd = request.payload.get("cwd")
    return find_definition(agent, cwd if isinstance(cwd, str) else None, locations.config)
