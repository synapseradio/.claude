"""A delegate's model fact: the harness's sources in its own order, or the force lever in effect."""

import pathlib
from collections.abc import Callable, Iterable, Mapping

from rulesets.facts.model.agent import (
    INHERIT,
    AgentModel,
    ListedBuiltIn,
    Pin,
    agent_model,
    listed_pin,
)
from rulesets.facts.model.claim import claim_model
from rulesets.facts.model.fact import FromForceLever, ModelResolution, ModelSource
from rulesets.facts.model.levers import (
    COORDINATOR_FORCE,
    SUBAGENT_FORCE,
    active_lever,
    subagent_default,
)
from rulesets.facts.model.record import read_model_record
from rulesets.facts.model.spawn import spawn_model
from rulesets.notices import Notice, provider_notices

type Settle = Callable[[object, ModelSource], ModelResolution]


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
    `inherit` names the parent's identifier and ends the search. Explore and Plan skip
    the default variable and list a model of their own.

    A force lever ignores the caller's model and the agent's pin: the coordinator lever
    gives the parent's identifier, the subagent lever the default variable's or, where it is
    empty, the parent's.
    """

    session_id = _text(payload.get("session_id"))
    agent_type = _text(payload.get("agent_type"))
    cwd = _text(payload.get("cwd"))
    parent = read_model_record(session_id, state_dir) if session_id else None
    notices: list[Notice] = [*provider_notices(env)]

    def settle(identifier: object, source: ModelSource) -> ModelResolution:
        return ModelResolution(claim_model(identifier, source, models, env), tuple(notices))

    agent = agent_model(agent_type, cwd, config_dir) if agent_type else None
    lever = active_lever(env)
    if lever == COORDINATOR_FORCE:
        return settle(parent, FromForceLever(lever))
    if lever == SUBAGENT_FORCE:
        return _under_subagent_force(agent, parent, env, settle)

    spawn = spawn_model(session_id, _text(payload.get("prompt_id")), agent_type, state_dir)
    notices += spawn.notices
    if isinstance(spawn.identifier, str):
        return settle(spawn.identifier, "per-spawn")

    match agent:
        case ListedBuiltIn():
            return _from_listed(agent, parent, env, settle, "parent-record")
        case Pin(identifier=identifier) if identifier == INHERIT:
            return settle(parent, "parent-record")
        case Pin(identifier=identifier, source=source):
            return settle(identifier, source)
        case None:
            default = subagent_default(env)
            if default:
                return settle(default, "subagent-default-variable")
            return settle(parent, "parent-record")


def _under_subagent_force(
    agent: AgentModel,
    parent: str | None,
    env: Mapping[str, str],
    settle: Settle,
) -> ModelResolution:
    """The default variable, then Explore's listed model, then the parent's identifier."""

    source = FromForceLever(SUBAGENT_FORCE)
    default = subagent_default(env)
    if default:
        return settle(default, source)
    if isinstance(agent, ListedBuiltIn):
        return _from_listed(agent, parent, env, settle, source)
    return settle(parent, source)


def _from_listed(
    agent: ListedBuiltIn,
    parent: str | None,
    env: Mapping[str, str],
    settle: Settle,
    parents_source: ModelSource,
) -> ModelResolution:
    pin = listed_pin(agent, parent, env)
    if pin is None:
        return settle(parent, parents_source)
    return settle(pin.identifier, pin.source)


def _text(value: object) -> str | None:
    return value if isinstance(value, str) and value else None
