"""The JSON a hook prints, and which events show the person a message."""

from __future__ import annotations

import dataclasses
import json
from collections.abc import Mapping

# A SubagentStart message lands in the subagent's own transcript and reaches no one else, so
# that event sends none (observed on Claude Code 2.1.318).
MESSAGE_SHOWN: Mapping[str, bool] = {"SessionStart": True, "SubagentStart": False}


@dataclasses.dataclass(frozen=True)
class PartOutput:
    """What one part sends: text for the agent's context and a message for the person."""

    context: str | None = None
    message: str | None = None


def hook_output(event: str, part: PartOutput) -> str:
    """The agent's context under `additionalContext` and the person's message under `systemMessage`.

    An empty output stands for a part with nothing to say.
    """

    output: dict[str, object] = {}
    if part.context:
        output["hookSpecificOutput"] = {"hookEventName": event, "additionalContext": part.context}
    if part.message:
        output["systemMessage"] = part.message
    return json.dumps(output) if output else ""
