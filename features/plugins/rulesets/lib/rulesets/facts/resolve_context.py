"""A delivery request turned into the facts of its context."""

from __future__ import annotations

import dataclasses
from collections.abc import Mapping

from rulesets.delivery.request import SessionStart, SubagentStart
from rulesets.facts.context import Facts
from rulesets.facts.flags import launch_flags
from rulesets.facts.model.delegate import resolve_delegate_model
from rulesets.facts.model.fact import ModelFact, claimed_name
from rulesets.facts.model.notice import model_notice
from rulesets.facts.model.session import resolve_session_model
from rulesets.locations import Locations
from rulesets.notices import Notice, absent_agent_notice, flag_notice
from rulesets.source.condition import ConditionError, fact_tests, parse_condition
from rulesets.source.directory import Present, RulesetsDirectory
from rulesets.source.manifest import Manifest


@dataclasses.dataclass(frozen=True)
class ResolvedContext:
    """The facts a context is composed from, the model fact behind them, and the notices raised."""

    facts: Facts
    model: ModelFact
    notices: tuple[Notice, ...]


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
            agent, kind = request.agent, "session"
        case SubagentStart():
            resolution = resolve_delegate_model(
                request.payload, models, environ, locations.state, locations.config
            )
            agent, kind = request.agent_type, "delegate"
    notices = [*resolution.notices]
    if (notice := model_notice(resolution.fact)) is not None:
        notices.append(notice)
    notices.extend(flag_notice(name) for name in launched.undeclared)
    if agent is None and _tests_agent(manifest):
        notices.append(absent_agent_notice())
    facts = Facts(claimed_name(resolution.fact), agent, kind, launched.declared)
    return ResolvedContext(facts, resolution.fact, tuple(notices))


def _tests_agent(manifest: Manifest | None) -> bool:
    if manifest is None:
        return False
    for item in manifest.items:
        try:
            tests = fact_tests(parse_condition(item.condition))
        except ConditionError:
            continue
        if any(test.fact == "agent" for test in tests):
            return True
    return False
