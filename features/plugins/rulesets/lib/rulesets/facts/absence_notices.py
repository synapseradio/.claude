"""The notices for an absent agent or tools fact that a condition of the config tested."""

from __future__ import annotations

from rulesets.facts.context import Absent, AllToolsBut, ListedTools
from rulesets.notices import Notice, absent_agent_notice, absent_tools_notice
from rulesets.source.condition import ConditionError, fact_tests, parse_condition
from rulesets.source.config import Config


def absent_fact_notices(
    config: Config | None, agent: str | Absent, tools: ListedTools | AllToolsBut | Absent
) -> tuple[Notice, ...]:
    """A notice for each of the agent and tools facts that is absent and that a condition tests."""

    notices: list[Notice] = []
    if isinstance(agent, Absent) and _tests(config, "agent"):
        notices.append(absent_agent_notice())
    if isinstance(tools, Absent) and _tests(config, "tools"):
        notices.append(absent_tools_notice(None if isinstance(agent, Absent) else agent))
    return tuple(notices)


def _tests(config: Config | None, fact: str) -> bool:
    if config is None:
        return False
    for block in config.blocks:
        try:
            tests = fact_tests(parse_condition(block.condition))
        except ConditionError:
            continue
        if any(test.fact == fact for test in tests):
            return True
    return False
