"""Parse a block's condition into a tree of fact tests, and evaluate it over a context.

A condition tests facts with `model <name>...`, `agent <name>...`, `kind session|delegate|any`,
`tools <Tool>...`, `flag <name>...`, and `session <id>...`, and combines the tests with `and`,
`or`, `not`, and parentheses. A test naming several values reads as those tests joined by `or`
and grouped, so `not model small large` negates the whole group. `not` binds tighter than
`and`, and `and` tighter than `or`. A run of one operator groups to the left.
"""

from __future__ import annotations

import dataclasses
import functools
import re
from collections.abc import Callable
from enum import Enum
from typing import Literal, assert_never, get_args

from rulesets.facts.context import Absent, Facts, Kind, NoClaim

type Fact = Literal["model", "agent", "kind", "tools", "flag", "session"]

FACTS: tuple[str, ...] = get_args(Fact.__value__)
KIND_ANY = "any"
_KIND_TESTS: tuple[str, ...] = (*get_args(Kind.__value__), KIND_ANY)
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


def _is_value(token: str | None) -> bool:
    return token is not None and token not in _KEYWORDS and token not in ("(", ")")


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
        if not _is_value(value):
            found = "the end of the condition" if value is None else f"`{value}`"
            raise ConditionError(f"`{token}` needs a name, found {found}")
        tests: list[Condition] = []
        while _is_value(value := self._peek()):
            if value in FACTS and tests and not (token == "kind" and value in _KIND_TESTS):
                raise ConditionError(f"expected `and` or `or` before `{value}`")
            self._take()
            if token == "kind" and value not in _KIND_TESTS:
                raise ConditionError(
                    f"`kind {value}` is no kind; kind tests session, delegate, or any"
                )
            tests.append(FactTest(token, value))
        return functools.reduce(Or, tests)


def parse_condition(text: str) -> Condition:
    """Parse the text of a condition. Raises ConditionError where it is no condition of facts."""

    return _Reader(_TOKEN.findall(text)).condition()


class Truth(Enum):
    """What a condition evaluates to: a block applies only where it is TRUE."""

    TRUE = "true"
    FALSE = "false"
    UNKNOWN = "unknown"

    @staticmethod
    def of(holds: bool) -> Truth:
        return Truth.TRUE if holds else Truth.FALSE

    def negated(self) -> Truth:
        match self:
            case Truth.TRUE:
                return Truth.FALSE
            case Truth.FALSE:
                return Truth.TRUE
            case Truth.UNKNOWN:
                return Truth.UNKNOWN

    def both(self, other: Truth) -> Truth:
        if Truth.FALSE in (self, other):
            return Truth.FALSE
        if Truth.UNKNOWN in (self, other):
            return Truth.UNKNOWN
        return Truth.TRUE

    def either(self, other: Truth) -> Truth:
        if Truth.TRUE in (self, other):
            return Truth.TRUE
        if Truth.UNKNOWN in (self, other):
            return Truth.UNKNOWN
        return Truth.FALSE


def evaluate_with(condition: Condition, truth_of: Callable[[FactTest], Truth]) -> Truth:
    """Three-valued evaluation where `truth_of` says what one fact test evaluates to."""

    match condition:
        case FactTest():
            return truth_of(condition)
        case Not(operand):
            return evaluate_with(operand, truth_of).negated()
        case And(left, right):
            return evaluate_with(left, truth_of).both(evaluate_with(right, truth_of))
        case Or(left, right):
            return evaluate_with(left, truth_of).either(evaluate_with(right, truth_of))
        case _:
            assert_never(condition)


def evaluate(condition: Condition, facts: Facts) -> Truth:
    """A test over an absent fact is UNKNOWN, and over an unclaimed model FALSE."""

    def truth_of(test: FactTest) -> Truth:
        match test:
            case FactTest("model", name):
                match facts.model:
                    case Absent():
                        return Truth.UNKNOWN
                    case NoClaim():
                        return Truth.FALSE
                    case claimed:
                        return Truth.of(claimed == name)
            case FactTest("agent", name):
                return _known_equal(facts.agent, name)
            case FactTest("kind", name):
                return Truth.TRUE if name == KIND_ANY else _known_equal(facts.kind, name)
            case FactTest("tools", name):
                match facts.tools:
                    case Absent():
                        return Truth.UNKNOWN
                    case held:
                        return Truth.of(held.holds(name))
            case FactTest("flag", name):
                return Truth.of(name in facts.flags)
            case FactTest("session", name):
                return _known_equal(facts.session, name)
            case _:
                assert_never(test)

    return evaluate_with(condition, truth_of)


def _known_equal(fact: str | Absent, name: str) -> Truth:
    return Truth.UNKNOWN if isinstance(fact, Absent) else Truth.of(fact == name)


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
