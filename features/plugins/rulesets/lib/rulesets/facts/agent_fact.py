"""The agent fact: the `agent_type` the harness's start payload carries."""

from rulesets.delivery.request import SessionStart, SubagentStart
from rulesets.facts.context import ABSENT, Absent


def agent_fact(request: SessionStart | SubagentStart) -> str | Absent:
    """The agent type of a delegate, or of a session started with `--agent`; ABSENT otherwise."""

    agent = request.agent if isinstance(request, SessionStart) else request.agent_type
    return ABSENT if agent is None else agent
