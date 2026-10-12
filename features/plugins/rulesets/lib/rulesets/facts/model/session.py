"""A main session's model fact: the harness's model, the environment, the record, or a switch."""

import pathlib
from collections.abc import Iterable, Mapping

from rulesets.facts.model.claim import claim_model
from rulesets.facts.model.fact import FromVariable, ModelFact, ModelResolution, SessionVariable
from rulesets.facts.model.record import read_model_record
from rulesets.notices import provider_notices

SESSION_VARIABLES: tuple[SessionVariable, ...] = ("ANTHROPIC_MODEL", "ANTHROPIC_DEFAULT_MODEL")


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

    return ModelResolution(_session_fact(payload, models, env, state_dir), provider_notices(env))


def _session_fact(
    payload: Mapping[str, object],
    models: Iterable[str],
    env: Mapping[str, str],
    state_dir: pathlib.Path,
) -> ModelFact:
    # SessionStart input may carry the model: https://code.claude.com/docs/en/hooks.md
    reported = payload.get("model")
    if reported not in (None, ""):
        return claim_model(reported, "harness-reported", models, env)

    for variable in SESSION_VARIABLES:
        value = env.get(variable)
        if value:
            return claim_model(value, FromVariable(variable, value), models, env)

    session_id = payload.get("session_id")
    recorded = (
        read_model_record(session_id, state_dir)
        if isinstance(session_id, str) and session_id
        else None
    )
    return claim_model(recorded, "session-record", models, env)


def resolve_switch_model(
    payload: Mapping[str, object],
    models: Iterable[str],
    env: Mapping[str, str],
) -> ModelResolution:
    """The model fact for the delivery that follows a model switch: the switch's target."""

    fact = claim_model(payload.get("to_model"), "switch-target", models, env)
    return ModelResolution(fact, provider_notices(env))
