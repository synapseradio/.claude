"""A delegate's model fact: the harness's sources in its own order, or the force lever in effect."""

import pathlib
from collections.abc import Iterable, Mapping
from typing import assert_never

from rulesets.facts.model.agent import (
    AgentModel,
    Inherit,
    ListedBuiltIn,
    Pin,
    agent_model,
    listed_pin,
)
from rulesets.facts.model.claim import claim_model
from rulesets.facts.model.fact import (
    ForceLever,
    FromForceLever,
    IdentifierSource,
    ModelResolution,
)
from rulesets.facts.model.levers import active_lever, subagent_default
from rulesets.facts.model.record import read_model_record
from rulesets.facts.model.spawn import spawn_model
from rulesets.notices import provider_notices

type Candidate = tuple[str | None, IdentifierSource]


def resolve_delegate_model(
    payload: Mapping[str, object],
    models: Iterable[str],
    env: Mapping[str, str],
    state_dir: pathlib.Path,
    config_dir: pathlib.Path,
) -> ModelResolution:
    """A delegate's model fact.

    With no force lever set, the first of four sources that names a string decides: the
    caller's model for the spawn, the agent's pin, `CLAUDE_CODE_SUBAGENT_MODEL`, then the
    parent session's recorded identifier
    (https://code.claude.com/docs/en/sub-agents.md#choose-a-model). A source naming no
    string yields to the next, a string no declared name claims stands, and a pin of
    `inherit` names the parent's identifier and ends the search.

    A force lever ignores the caller's model and the agent's pin: the coordinator lever
    gives the parent's identifier, the subagent lever the default variable's or, where it is
    empty, the parent's.
    """

    session_id = _text(payload.get("session_id"))
    agent_type = _text(payload.get("agent_type"))
    cwd = _text(payload.get("cwd"))
    parent = read_model_record(session_id, state_dir) if session_id else None
    notices = [*provider_notices(env)]

    candidate: Candidate
    lever = active_lever(env)
    match lever:
        case ForceLever.COORDINATOR:
            candidate = parent, FromForceLever(lever)
        case ForceLever.SUBAGENT:
            agent = _agent(agent_type, cwd, config_dir)
            candidate = _under_subagent_force(agent, parent, env)
        case None:
            spawn = spawn_model(session_id, _text(payload.get("prompt_id")), agent_type, state_dir)
            notices += spawn.notices
            if isinstance(spawn.identifier, str):
                candidate = spawn.identifier, "per-spawn"
            else:
                candidate = _from_agent(_agent(agent_type, cwd, config_dir), parent, env)
        case _:
            assert_never(lever)

    identifier, source = candidate
    return ModelResolution(claim_model(identifier, source, models, env), tuple(notices))


def _agent(agent_type: str | None, cwd: str | None, config_dir: pathlib.Path) -> AgentModel:
    return agent_model(agent_type, cwd, config_dir) if agent_type else None


def _under_subagent_force(
    agent: AgentModel, parent: str | None, env: Mapping[str, str]
) -> Candidate:
    """The default variable, then Explore's listed model, then the parent's identifier."""

    source = FromForceLever(ForceLever.SUBAGENT)
    default = subagent_default(env)
    if default:
        return default, source
    if isinstance(agent, ListedBuiltIn):
        return _listed_or_parent(agent, parent, env, source)
    return parent, source


def _from_agent(agent: AgentModel, parent: str | None, env: Mapping[str, str]) -> Candidate:
    """What the agent's definition or built-in entry leaves of the three later sources."""

    match agent:
        case ListedBuiltIn():
            return _listed_or_parent(agent, parent, env, "parent-record")
        case Inherit():
            return parent, "parent-record"
        case Pin(identifier=identifier, source=source):
            return identifier, source
        case None:
            default = subagent_default(env)
            if default:
                return default, "subagent-default-variable"
            return parent, "parent-record"
        case _:
            assert_never(agent)


def _listed_or_parent(
    agent: ListedBuiltIn,
    parent: str | None,
    env: Mapping[str, str],
    parents_source: IdentifierSource,
) -> Candidate:
    pin = listed_pin(agent, parent, env)
    if pin is None:
        return parent, parents_source
    return pin.identifier, pin.source


def _text(value: object) -> str | None:
    return value if isinstance(value, str) and value else None
