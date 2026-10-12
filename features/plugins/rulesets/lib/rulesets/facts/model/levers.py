"""The two environment levers that override the models a delegate's caller and definition name."""

from collections.abc import Mapping

from rulesets.facts.environment import flag_is_set
from rulesets.facts.model.fact import ForceLever

SUBAGENT_FORCE: ForceLever = "CLAUDE_CODE_SUBAGENT_MODEL_FORCE"
COORDINATOR_FORCE: ForceLever = "CLAUDE_CODE_COORDINATOR_FORCE_WORKER_INHERIT_MODEL"


def active_lever(env: Mapping[str, str]) -> ForceLever | None:
    """The force lever in effect, the coordinator lever ahead of the subagent one.

    The harness suppresses the model parameter under either lever
    (https://code.claude.com/docs/en/sub-agents.md#choose-a-model). The coordinator lever
    also fixes the delegate to the parent's model, so it decides where both are set.
    """

    for lever in (COORDINATOR_FORCE, SUBAGENT_FORCE):
        if flag_is_set(env, lever):
            return lever
    return None
