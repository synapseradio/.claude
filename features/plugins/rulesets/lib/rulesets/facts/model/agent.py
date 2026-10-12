"""What fixes an agent type's model: its definition, or the harness's table for built-in agents."""

import pathlib
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Literal

from rulesets.facts.environment import flag_is_set
from rulesets.facts.model.agent_definition import definition_front
from rulesets.facts.model.claim import opens_on

INHERIT = "inherit"

# Built-in agents carry no definition file, so their pins come from the table at
# https://code.claude.com/docs/en/sub-agents.md#built-in-subagents. The built-ins that
# inherit the main conversation's model pin nothing.
BUILT_IN_PINS = {"claude-code-guide": "haiku", "statusline-setup": "sonnet"}

FABLE_NAME = "fable"
EXPLORE_UNDER_FABLE = "opus"
PROVIDER_VARIABLES = (
    "CLAUDE_CODE_USE_BEDROCK",
    "CLAUDE_CODE_USE_MANTLE",
    "CLAUDE_CODE_USE_VERTEX",
    "CLAUDE_CODE_USE_FOUNDRY",
    "CLAUDE_CODE_USE_ANTHROPIC_AWS",
)


@dataclass(frozen=True)
class Pin:
    """The identifier an agent type is pinned to, which may be `inherit`, and what pinned it."""

    identifier: str
    source: Literal["definition-pin", "built-in-pin"]


@dataclass(frozen=True)
class ListedBuiltIn:
    """The built-in Explore or Plan agent, which no definition file replaces.

    Both list a model of their own and skip `CLAUDE_CODE_SUBAGENT_MODEL` unless a force
    lever is set (https://code.claude.com/docs/en/sub-agents.md#built-in-subagents).
    """

    agent_type: Literal["Explore", "Plan"]


type AgentModel = Pin | ListedBuiltIn | None


def agent_model(agent_type: str, cwd: str | None, config_dir: pathlib.Path) -> AgentModel:
    """What fixes the model of `agent_type`, or None where nothing does.

    A definition that names a string model pins it. A definition that names none hides
    the built-in agent of the same type. A plugin-scoped type never names a built-in agent.
    """

    front = definition_front(agent_type, cwd, config_dir)
    if front is not None:
        model = front.get("model")
        return Pin(model, "definition-pin") if isinstance(model, str) and model else None
    if ":" in agent_type:
        return None
    match agent_type:
        case "Explore" | "Plan":
            return ListedBuiltIn(agent_type)
        case _:
            built_in = BUILT_IN_PINS.get(agent_type)
            return Pin(built_in, "built-in-pin") if built_in else None


def listed_pin(agent: ListedBuiltIn, parent: str | None, env: Mapping[str, str]) -> Pin | None:
    """The pin Explore or Plan lists, or None where it lists the parent's model.

    Explore lists the `opus` alias where the parent runs a Fable model and none of the
    provider variables is set; every other case lists the parent's model
    (https://code.claude.com/docs/en/sub-agents.md#built-in-subagents). The Fable test
    reads the parent's full recorded identifier and holds where it opens on `claude-fable`
    at a claim boundary, as the context-facts spec states, so the bare alias `fable` does
    not hold. A Claude apps gateway sets no provider variable, so the alias applies there
    although the harness keeps the parent's model.
    """

    fable_parent = parent is not None and opens_on(parent, FABLE_NAME)
    direct = not any(flag_is_set(env, variable) for variable in PROVIDER_VARIABLES)
    if agent.agent_type == "Explore" and fable_parent and direct:
        return Pin(EXPLORE_UNDER_FABLE, "built-in-pin")
    return None
