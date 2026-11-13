"""Events a suite run emits as it waits, starts, counts, finishes tests, and ends."""

from dataclasses import dataclass
from typing import Literal

type TestOutcome = Literal["pass", "fail", "skip"]


@dataclass(frozen=True)
class SuiteWaiting:
    suite: str


@dataclass(frozen=True)
class SuiteStarted:
    suite: str
    workers: int


@dataclass(frozen=True)
class TestsCounted:
    suite: str
    total: int


@dataclass(frozen=True)
class TestEnded:
    suite: str
    file: str
    name: str
    outcome: TestOutcome
    seconds: float | None


@dataclass(frozen=True)
class SuiteEnded:
    suite: str
    status: TestOutcome
    line: str


type Event = SuiteWaiting | SuiteStarted | TestsCounted | TestEnded | SuiteEnded
