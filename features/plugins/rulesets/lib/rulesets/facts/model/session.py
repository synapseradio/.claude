"""A main session's model fact: the harness's model, the environment, the record, or a switch."""

import pathlib
from collections.abc import Iterable, Mapping
from typing import get_args

from rulesets.facts.model.claim import claim_model
from rulesets.facts.model.fact import FromVariable, ModelFact, ModelResolution, SessionVariable
from rulesets.facts.model.record import read_model_record
from rulesets.notices import disregarded_variable_notices

SESSION_VARIABLES: tuple[SessionVariable, ...] = get_args(SessionVariable.__value__)


def resolve_session_model(
    payload: Mapping[str, object],
    models: Iterable[str],
    env: Mapping[str, str],
    state_dir: pathlib.Path,
) -> ModelResolution:
    """A session's model fact: the harness's model, then the environment, then the session's record.

    The first source that names an identifier stands, claimed or not. A reported value that is
    not a string leaves the model missing and passes to no later source.
    """

    fact = _session_fact(payload, models, env, state_dir)
    if isinstance(fact.source, FromVariable):
        return ModelResolution(fact, disregarded_variable_notices(env, fact.source.name))
    return ModelResolution(fact, ())


def _session_fact(
    payload: Mapping[str, object],
    models: Iterable[str],
    env: Mapping[str, str],
    state_dir: pathlib.Path,
) -> ModelFact:
    # SessionStart input may carry the model: https://code.claude.com/docs/en/hooks.md
    reported = payload.get("model")
    if reported not in (None, ""):
        return claim_model(reported, "harness-reported", models)

    for variable in SESSION_VARIABLES:
        value = env.get(variable)
        if value:
            return claim_model(value, FromVariable(variable, value), models)

    session_id = payload.get("session_id")
    recorded = (
        read_model_record(session_id, state_dir)
        if isinstance(session_id, str) and session_id
        else None
    )
    return claim_model(recorded, "session-record", models)


def resolve_switch_model(
    payload: Mapping[str, object],
    models: Iterable[str],
) -> ModelResolution:
    """The model fact for the delivery that follows a model switch: the switch's target."""

    return ModelResolution(claim_model(payload.get("to_model"), "switch-target", models), ())
