"""Parses each test framework's output, one line at a time, into per-test events."""

import re
from typing import Literal, Protocol

from events import Event, TestEnded, TestOutcome, TestsCounted

type SuiteKind = Literal["pytest", "bats", "mod"]

NUMBER = r"[0-9]{1,9}"
DECIMAL = r"[0-9]{1,9}(?:\.[0-9]{1,9})?"

PYTEST_OUTCOMES: dict[str, TestOutcome] = {
    "PASSED": "pass",
    "XPASS": "pass",
    "FAILED": "fail",
    "ERROR": "fail",
    "SKIPPED": "skip",
    "XFAIL": "skip",
}
PYTEST_WORDS = "|".join(PYTEST_OUTCOMES)
PYTEST_COUNT = re.compile(rf"collected ({NUMBER}) items?\b|^[0-9]+ workers? \[({NUMBER}) items?\]")
PYTEST_FINISHED = re.compile(
    rf"^(?P<path>[^\s:]+)::(?P<name>.*?) +(?P<outcome>{PYTEST_WORDS})(?: .*)?$"
)
PYTEST_WORKER_FINISHED = re.compile(
    rf"^\[gw[0-9]+\] \[ *[0-9]+%\] (?P<outcome>{PYTEST_WORDS}) "
    r"(?P<path>[^\s:]+)::(?P<name>.*?) *$"
)

BATS_COUNT = re.compile(rf"^1\.\.({NUMBER})$")
BATS_FINISHED = re.compile(
    rf"^(?P<not>not )?ok {NUMBER} (?P<rest>.+?)(?: in (?P<ms>{NUMBER})ms)?(?P<skip> # skip(?: .*)?)?$"
)

MOD_COUNT = re.compile(rf"^Ran ({NUMBER}) tests? across ")
MOD_HEADER = re.compile(r"^([^\s(].*):$")
MOD_FINISHED = re.compile(
    rf"^\((?P<outcome>pass|fail|skip|todo)\) (?P<name>.+?)"
    rf"(?: \[(?P<time>{DECIMAL})(?P<unit>ms|s|us|µs|ns)\])?$"
)
MOD_OUTCOMES: dict[str, TestOutcome] = {
    "pass": "pass",
    "fail": "fail",
    "skip": "skip",
    "todo": "skip",
}
MOD_UNIT_EXPONENTS = {"s": 0, "ms": -3, "us": -6, "µs": -6, "ns": -9}


class Parser(Protocol):
    def feed(self, line: str) -> list[Event]: ...


def join_root(root: str, path: str) -> str:
    return f"{root}/{path}" if root and path else path


class PytestParser:
    def __init__(self, suite: str, root: str) -> None:
        self.suite = suite
        self.root = root
        self.counted = False

    def feed(self, line: str) -> list[Event]:
        finished = PYTEST_WORKER_FINISHED.match(line) or PYTEST_FINISHED.match(line)
        if finished:
            return [
                TestEnded(
                    self.suite,
                    join_root(self.root, finished["path"]),
                    finished["name"],
                    PYTEST_OUTCOMES[finished["outcome"]],
                    None,
                )
            ]
        total = PYTEST_COUNT.search(line)
        if total and not self.counted:
            self.counted = True
            return [TestsCounted(self.suite, int(total[1] or total[2]))]
        return []


class BatsParser:
    def __init__(self, suite: str) -> None:
        self.suite = suite
        self.counted = False

    def feed(self, line: str) -> list[Event]:
        total = BATS_COUNT.match(line)
        if total and not self.counted:
            self.counted = True
            return [TestsCounted(self.suite, int(total[1]))]
        finished = BATS_FINISHED.match(line)
        if not finished:
            return []
        outcome: TestOutcome = "fail" if finished["not"] else "pass"
        if finished["skip"]:
            outcome = "skip"
        seconds = int(finished["ms"]) / 1000 if finished["ms"] else None
        return [TestEnded(self.suite, "", finished["rest"], outcome, seconds)]


class ModParser:
    def __init__(self, suite: str, root: str) -> None:
        self.suite = suite
        self.root = root
        self.file = ""
        self.counted = False

    def feed(self, line: str) -> list[Event]:
        finished = MOD_FINISHED.match(line)
        if finished:
            seconds = (
                float(f"{finished['time']}e{MOD_UNIT_EXPONENTS[finished['unit']]}")
                if finished["time"]
                else None
            )
            return [
                TestEnded(
                    self.suite,
                    join_root(self.root, self.file),
                    finished["name"],
                    MOD_OUTCOMES[finished["outcome"]],
                    seconds,
                )
            ]
        total = MOD_COUNT.match(line)
        if total and not self.counted:
            self.counted = True
            return [TestsCounted(self.suite, int(total[1]))]
        header = MOD_HEADER.match(line)
        if header:
            self.file = header[1]
        return []


def parser_for(kind: SuiteKind, suite: str, root: str) -> Parser:
    match kind:
        case "pytest":
            return PytestParser(suite, root)
        case "bats":
            return BatsParser(suite)
        case "mod":
            return ModParser(suite, root)


def extra_argv(kind: SuiteKind) -> list[str]:
    match kind:
        case "pytest":
            return ["-v"]
        case "bats":
            return ["--timing"]
        case "mod":
            return []
