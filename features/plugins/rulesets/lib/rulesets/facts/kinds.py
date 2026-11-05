"""The fact kinds a condition tests, and the rank a block takes from them."""

from enum import IntEnum

from rulesets.source.condition import Condition, fact_tests


class Rank(IntEnum):
    """Where a block stands among the blocks of one band, lowest first."""

    NONE = 0
    MODEL = 1
    AGENT_KIND_TOOLS = 2
    FLAG = 3
    SESSION = 4


_FACT_RANKS: dict[str, Rank] = {
    "model": Rank.MODEL,
    "agent": Rank.AGENT_KIND_TOOLS,
    "kind": Rank.AGENT_KIND_TOOLS,
    "tools": Rank.AGENT_KIND_TOOLS,
    "flag": Rank.FLAG,
    "session": Rank.SESSION,
}


def block_rank(condition: Condition) -> Rank:
    """The highest rank among the facts the condition tests."""

    return max(_FACT_RANKS[test.fact] for test in fact_tests(condition))
