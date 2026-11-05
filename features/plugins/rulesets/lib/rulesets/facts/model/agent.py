"""What fixes an agent type's model: its definition, or the harness's table for built-in agents."""

import pathlib
from dataclasses import dataclass
from typing import Literal

from rulesets.facts.agent_definition import definition_front
from rulesets.facts.model.fact import NotAString

_INHERIT = "inherit"

# Built-in agents carry no definition file, so their pins come from the table at
# https://code.claude.com/docs/en/sub-agents.md#built-in-subagents. The built-ins that
# inherit the main conversation's model pin nothing.
BUILT_IN_PINS = {"claude-code-guide": "haiku", "statusline-setup": "sonnet"}


@dataclass(frozen=True)
class Pin:
    """The identifier an agent type is pinned to, and what pinned it."""

    identifier: str
    source: Literal["definition-pin", "built-in-pin"]


@dataclass(frozen=True)
class Inherit:
    """A definition whose model is `inherit`, which runs the agent on its parent's model."""


type AgentModel = Pin | Inherit | NotAString | None


def agent_model(agent_type: str, cwd: str | None, config_dir: pathlib.Path) -> AgentModel:
    """What fixes the model of `agent_type`, or None where nothing does.

    A definition that names a string model pins it, and one that names a value of another
    type is a pin that is not a string. A definition that names none hides the built-in
    agent of the same type. A plugin-scoped type never names a built-in agent.
    """

    front = definition_front(agent_type, cwd, config_dir)
    if front is not None:
        model = front.get("model")
        if model is None or model == "":
            return None
        if not isinstance(model, str):
            return NotAString(model, "definition-pin")
        return Inherit() if model == _INHERIT else Pin(model, "definition-pin")
    if ":" in agent_type:
        return None
    built_in = BUILT_IN_PINS.get(agent_type)
    return Pin(built_in, "built-in-pin") if built_in else None
