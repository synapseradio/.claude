"""Whether some context makes a condition true, given that a context has one model, agent, kind, and session."""

from __future__ import annotations

import itertools
from collections.abc import Callable

from rulesets.source.condition import Condition, FactTest, Truth, evaluate_with, fact_tests

_SINGLE_VALUED = ("model", "agent", "kind", "session")
_INDEPENDENT = ("flag", "tools")


def can_hold(condition: Condition) -> bool:
    """Whether some context makes `condition` true.

    A context holds at most one value of each single-valued fact, so tests of different
    values of one such fact never hold together; flags and tools are independent.
    """

    tests = fact_tests(condition)
    values = [sorted({t.value for t in tests if t.fact == fact}) for fact in _SINGLE_VALUED]
    flags = sorted({(t.fact, t.value) for t in tests if t.fact in _INDEPENDENT})
    for chosen in itertools.product(*([None, *each] for each in values)):
        picked = dict(zip(_SINGLE_VALUED, chosen, strict=True))
        for bits in itertools.product((False, True), repeat=len(flags)):
            held = {test for test, bit in zip(flags, bits, strict=True) if bit}

            if evaluate_with(condition, _truth_in(picked, held)) is Truth.TRUE:
                return True
    return False


def _truth_in(
    picked: dict[str, str | None], held: set[tuple[str, str]]
) -> Callable[[FactTest], Truth]:
    def truth_of(test: FactTest) -> Truth:
        if test.fact in _INDEPENDENT:
            return Truth.of((test.fact, test.value) in held)
        return Truth.of(picked[test.fact] == test.value)

    return truth_of
