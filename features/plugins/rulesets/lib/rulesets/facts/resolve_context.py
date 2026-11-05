"""A delivery request turned into the facts of its context."""

from __future__ import annotations

import dataclasses
from collections.abc import Mapping

from rulesets.delivery.request import SessionStart, SubagentStart
from rulesets.facts.agent_definition import definition_front
from rulesets.facts.agent_fact import agent_fact
from rulesets.facts.context import (
    ABSENT,
    UNCLAIMED,
    Absent,
    AllToolsBut,
    Facts,
    ListedTools,
    NoClaim,
)
from rulesets.facts.flags import FlagFact, delegate_flags, launch_flags, session_flags
from rulesets.facts.model.delegate import resolve_delegate_model
from rulesets.facts.model.fact import Claimed, Missing, ModelFact, Unclaimed
from rulesets.facts.model.notice import model_notice
from rulesets.facts.model.session import resolve_session_model
from rulesets.facts.tools_fact import tools_fact
from rulesets.locations import Locations
from rulesets.notices import Notice, absent_agent_notice, absent_tools_notice, flag_notice
from rulesets.session.state import read_state
from rulesets.source.condition import ConditionError, fact_tests, parse_condition
from rulesets.source.directory import Present, RulesetsDirectory
from rulesets.source.manifest import Manifest


@dataclasses.dataclass(frozen=True)
class ResolvedContext:
    """The facts a context is composed from, the model fact and flags behind them, and the notices raised."""

    facts: Facts
    model: ModelFact
    notices: tuple[Notice, ...]
    flags: tuple[FlagFact, ...]


def resolve_context(
    request: SessionStart | SubagentStart,
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
    if isinstance(agent, Absent) and _tests(manifest, "agent"):
        notices.append(absent_agent_notice())
    tools = _tools_of(agent, request, locations)
    if isinstance(tools, Absent) and _tests(manifest, "tools"):
        notices.append(absent_tools_notice(None if isinstance(agent, Absent) else agent))
    facts = Facts(
        _model_in_facts(resolution.fact),
        agent,
        kind,
        frozenset(flag.name for flag in flags),
        request.session_id,
        tools,
    )
    return ResolvedContext(facts, resolution.fact, tuple(notices), flags)


def _model_in_facts(fact: ModelFact) -> str | NoClaim | Absent:
    match fact:
        case Claimed(name=name):
            return name
        case Unclaimed():
            return UNCLAIMED
        case Missing():
            return ABSENT


def _tools_of(
    agent: str | Absent, request: SessionStart | SubagentStart, locations: Locations
) -> ListedTools | AllToolsBut | Absent:
    if isinstance(agent, Absent):
        return ABSENT
    cwd = request.payload.get("cwd")
    return tools_fact(
        definition_front(agent, cwd if isinstance(cwd, str) else None, locations.config)
    )


def _tests(manifest: Manifest | None, fact: str) -> bool:
    if manifest is None:
        return False
    for item in manifest.items:
        try:
            tests = fact_tests(parse_condition(item.condition))
        except ConditionError:
            continue
        if any(test.fact == fact for test in tests):
            return True
    return False
