"""Whether some context makes a condition true, given that a context has one model, agent, kind, and session."""

from __future__ import annotations

import itertools
from collections.abc import Callable

from rulesets.source.condition import Condition, FactTest, evaluate_with, fact_tests

_SINGLE_VALUED = ("model", "agent", "kind", "session")


def can_hold(condition: Condition) -> bool:
    """Whether some context makes `condition` true.

    A context holds at most one value of each single-valued fact, so tests of different
    values of one such fact never hold together; flags are independent.
    """

    tests = fact_tests(condition)
    values = [sorted({t.value for t in tests if t.fact == fact}) for fact in _SINGLE_VALUED]
    flags = sorted({t.value for t in tests if t.fact == "flag"})
    for chosen in itertools.product(*([None, *each] for each in values)):
        picked = dict(zip(_SINGLE_VALUED, chosen, strict=True))
        for bits in itertools.product((False, True), repeat=len(flags)):
            set_flags = {flag for flag, bit in zip(flags, bits, strict=True) if bit}

            if evaluate_with(condition, _holds_in(picked, set_flags)):
                return True
    return False


def _holds_in(picked: dict[str, str | None], set_flags: set[str]) -> Callable[[FactTest], bool]:
    def holds(test: FactTest) -> bool:
        if test.fact == "flag":
            return test.value in set_flags
        return picked[test.fact] == test.value

    return holds
