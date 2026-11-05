"""A delegate's model fact: the harness's sources in its own order, or the force lever in effect."""

import pathlib
from collections.abc import Iterable, Mapping
from typing import assert_never

from rulesets.facts.model.agent import AgentModel, Inherit, Pin, agent_model
from rulesets.facts.model.claim import claim_model
from rulesets.facts.model.fact import (
    ForceLever,
    FromForceLever,
    IdentifierSource,
    ModelResolution,
    NotAString,
)
from rulesets.facts.model.levers import active_lever, subagent_default
from rulesets.facts.model.record import read_model_record
from rulesets.facts.model.spawn import spawn_model
from rulesets.notices import Notice

type Candidate = tuple[object, IdentifierSource]


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

    A caller's model or a pin that is not a string ends the search with a missing model.

    A force lever ignores the caller's model and the agent's pin: the coordinator lever
    gives the parent's identifier, the subagent lever the default variable's or, where it is
    empty, the parent's.
    """

    session_id = _text(payload.get("session_id"))
    agent_type = _text(payload.get("agent_type"))
    cwd = _text(payload.get("cwd"))

    parent = read_model_record(session_id, state_dir) if session_id else None
    notices: list[Notice] = []

    candidate: Candidate
    lever = active_lever(env)
    match lever:
        case ForceLever.COORDINATOR:
            candidate = parent, FromForceLever(lever)
        case ForceLever.SUBAGENT:
            candidate = subagent_default(env) or parent, FromForceLever(lever)
        case None:
            spawn = spawn_model(session_id, _text(payload.get("prompt_id")), agent_type, state_dir)
            notices += spawn.notices
            if spawn.identifier is not None:
                candidate = spawn.identifier, "per-spawn"
            else:
                agent = agent_model(agent_type, cwd, config_dir) if agent_type else None
                candidate = _from_agent(agent, parent, env)
        case _:
            assert_never(lever)

    identifier, source = candidate
    return ModelResolution(claim_model(identifier, source, models), tuple(notices))


def _from_agent(agent: AgentModel, parent: str | None, env: Mapping[str, str]) -> Candidate:
    """What the agent's definition or built-in entry leaves of the three later sources."""

    match agent:
        case Inherit():
            return parent, "parent-record"
        case Pin(identifier=identifier, source=source):
            return identifier, source
        case NotAString(value=value, source=source):
            return value, source
        case None:
            default = subagent_default(env)
            if default:
                return default, "subagent-default-variable"
            return parent, "parent-record"
        case _:
            assert_never(agent)


def _text(value: object) -> str | None:
    return value if isinstance(value, str) and value else None
