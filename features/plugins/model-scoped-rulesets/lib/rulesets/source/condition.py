"""Parse a `when` item's condition into a tree of fact tests, and evaluate it over a context.

A condition tests facts with `model <name>`, `agent <name>`, `kind session|delegate|fork`, and
`flag <name>`, and combines the tests with `and`, `or`, `not`, and parentheses. `not` binds
tighter than `and`, and `and` tighter than `or`. A run of one operator groups to the left.
"""

from __future__ import annotations

import dataclasses
import re
from typing import Literal, assert_never, get_args

from rulesets.facts import Facts, Kind

type Fact = Literal["model", "agent", "kind", "flag"]

FACTS: tuple[str, ...] = get_args(Fact.__value__)
_KINDS: tuple[str, ...] = get_args(Kind.__value__)
_KEYWORDS = ("and", "or", "not")
_TOKEN = re.compile(r"[()]|[^\s()]+")


class ConditionError(Exception):
    """Text that is no condition, or a condition that tests more than facts."""

    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


@dataclasses.dataclass(frozen=True)
class FactTest:
    fact: Fact
    value: str


@dataclasses.dataclass(frozen=True)
class Not:
    operand: Condition


@dataclasses.dataclass(frozen=True)
class And:
    left: Condition
    right: Condition


@dataclasses.dataclass(frozen=True)
class Or:
    left: Condition
    right: Condition


type Condition = FactTest | Not | And | Or


class _Reader:
    """Recursive descent over the tokens of one condition, loosest operator first."""

    def __init__(self, tokens: list[str]):
        self._tokens = tokens
        self._at = 0

    def _peek(self) -> str | None:
        return self._tokens[self._at] if self._at < len(self._tokens) else None

    def _take(self) -> str:
        token = self._tokens[self._at]
        self._at += 1
        return token

    def condition(self) -> Condition:
        if not self._tokens:
            raise ConditionError("the condition is empty")
        parsed = self._or()
        if (token := self._peek()) is not None:
            if token == ")":
                raise ConditionError(
                    "a closing parenthesis has no opening one; parentheses must balance"
                )
            raise ConditionError(f"expected `and` or `or` before `{token}`")
        return parsed

    def _or(self) -> Condition:
        left = self._and()
        while self._peek() == "or":
            self._take()
            left = Or(left, self._and())
        return left

    def _and(self) -> Condition:
        left = self._not()
        while self._peek() == "and":
            self._take()
            left = And(left, self._not())
        return left

    def _not(self) -> Condition:
        if self._peek() == "not":
            self._take()
            return Not(self._not())
        return self._primary()

    def _primary(self) -> Condition:
        token = self._peek()
        if token is None:
            raise ConditionError("the condition ends where a test was expected")
        if token == "(":
            self._take()
            inner = self._or()
            if self._peek() != ")":
                raise ConditionError(
                    "an opening parenthesis has no closing one; parentheses must balance"
                )
            self._take()
            return inner
        if token not in FACTS:
            if token in _KEYWORDS or token == ")":
                raise ConditionError(f"expected a test, found `{token}`")
            raise ConditionError(f"`{token}` tests no fact; a condition tests {', '.join(FACTS)}")
        self._take()
        value = self._peek()
        if value is None or value in _KEYWORDS or value in ("(", ")"):
            found = "the end of the condition" if value is None else f"`{value}`"
            raise ConditionError(f"`{token}` needs a name, found {found}")
        self._take()
        if token == "kind" and value not in _KINDS:
            raise ConditionError(
                f"`kind {value}` is no kind; kind tests session, delegate, or fork"
            )
        return FactTest(token, value)


def parse_condition(text: str) -> Condition:
    """Parse the text of a condition. Raises ConditionError where it is no condition of facts."""

    return _Reader(_TOKEN.findall(text)).condition()


def evaluate(condition: Condition, facts: Facts) -> bool:
    """Two-valued: a test over an absent fact is false, and its negation true."""

    match condition:
        case FactTest("model", name):
            return facts.model == name
        case FactTest("agent", name):
            return facts.agent == name
        case FactTest("kind", name):
            return facts.kind == name
        case FactTest("flag", name):
            return name in facts.flags
        case Not(operand):
            return not evaluate(operand, facts)
        case And(left, right):
            return evaluate(left, facts) and evaluate(right, facts)
        case Or(left, right):
            return evaluate(left, facts) or evaluate(right, facts)
        case _:
            assert_never(condition)


def fact_tests(condition: Condition) -> tuple[FactTest, ...]:
    """Every fact test in the condition, in reading order, a repeated test repeated."""

    match condition:
        case FactTest():
            return (condition,)
        case Not(operand):
            return fact_tests(operand)
        case And(left, right) | Or(left, right):
            return fact_tests(left) + fact_tests(right)
        case _:
            assert_never(condition)
