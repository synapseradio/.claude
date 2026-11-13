"""Verdicts read from each runner's output, printed as PASS and FAIL lines or one JSON object."""

import json
import re
import sys
from dataclasses import dataclass, field
from typing import Literal

from run import Finished
from scope import Skipped

FAILURE_LINES = 20
UNCOMMITTED_FIXES = "the pushed commits lack these fixes; commit them and push again"

type Status = Literal["pass", "fail", "skip"]


@dataclass(frozen=True)
class Counts:
    passed: int = 0
    failed: int = 0
    skipped: int = 0

    def describe(self) -> list[str]:
        parts = [(self.failed, "failed"), (self.passed, "passed"), (self.skipped, "skipped")]
        return [f"{count} {label}" for count, label in parts if count]


PYTEST_SUMMARY = re.compile(r"\bin \d+(?:\.\d+)?s\b")
PYTEST_COUNT = re.compile(r"(\d+) (passed|failed|skipped|errors?|xfailed|xpassed)\b")
TAP_RESULT = re.compile(r"^(not ok|ok)\b[^#]*(#\s*skip\b)?", re.IGNORECASE)
BUN_COUNT = re.compile(r"^\s*(\d+) (pass|fail|skip)(?:ed)?\b", re.MULTILINE)


def pytest_counts(output: str) -> Counts:
    """Counts from pytest's last summary line, `1 failed, 2 passed in 0.12s`; errors count as failures."""
    summaries = [line for line in output.splitlines() if PYTEST_SUMMARY.search(line)]
    if not summaries:
        return Counts()
    found = {"passed": 0, "failed": 0, "skipped": 0}
    for number, label in PYTEST_COUNT.findall(summaries[-1]):
        if label in ("passed", "xpassed"):
            found["passed"] += int(number)
        elif label in ("skipped", "xfailed"):
            found["skipped"] += int(number)
        else:
            found["failed"] += int(number)
    return Counts(**found)


def tap_counts(output: str) -> Counts:
    """Counts from bats TAP result lines.

    https://testanything.org/tap-specification.html
    """
    passed = failed = skipped = 0
    for line in output.splitlines():
        match = TAP_RESULT.match(line)
        if match is None:
            continue
        if match[1] == "not ok":
            failed += 1
        elif match[2]:
            skipped += 1
        else:
            passed += 1
    return Counts(passed, failed, skipped)


def bun_counts(output: str) -> Counts:
    """Counts from the `N pass` / `N fail` summary the mod runner prints, as bun test does."""
    found = {"pass": 0, "fail": 0, "skip": 0}
    for number, label in BUN_COUNT.findall(output):
        found[label] = int(number)
    return Counts(found["pass"], found["fail"], found["skip"])


def failure_lines(kind: str, output: str) -> list[str]:
    lines = output.splitlines()
    match kind:
        case "pytest":
            chosen = [line for line in lines if line.startswith("FAILED ")]
        case "bats":
            chosen = [line for line in lines if line.startswith("not ok")]
        case "mod":
            chosen = [line for line in lines if line.startswith("(fail)")]
        case _:
            chosen = [line for line in lines if line.strip()]
    return chosen[:FAILURE_LINES]


def counts_for(kind: str, output: str) -> Counts:
    match kind:
        case "pytest":
            return pytest_counts(output)
        case "bats":
            return tap_counts(output)
        case "mod":
            return bun_counts(output)
        case _:
            return Counts()


@dataclass(frozen=True)
class Outcome:
    name: str
    kind: str
    status: Status
    counts: Counts
    seconds: float
    log: str | None
    failures: list[str]
    command: list[str] | None
    reason: str | None = None
    fixed: list[str] = field(default_factory=list)

    @classmethod
    def of(cls, finished: Finished, prepush: bool = False) -> Outcome:
        """The verdict on a finished task; under `prepush`, files a fixer changed fail the job, because a push sends commits and not the working tree."""
        output = finished.log.read_text(encoding="utf-8", errors="replace")
        kind = finished.task.kind
        unpushable = prepush and bool(finished.fixed)
        if finished.exit == 0 and not unpushable:
            status: Status = "pass"
        elif finished.exit in finished.task.skip_exits:
            status = "skip"
        else:
            status = "fail"
        return cls(
            name=finished.task.name,
            kind=kind,
            status=status,
            counts=counts_for(kind, output),
            seconds=round(finished.seconds, 2),
            log=str(finished.log),
            failures=(
                [UNCOMMITTED_FIXES]
                if unpushable and finished.exit == 0
                else failure_lines(kind, output)
                if status == "fail"
                else []
            ),
            command=finished.command,
            fixed=list(finished.fixed),
        )

    @classmethod
    def skipped(cls, skip: Skipped) -> Outcome:
        return cls(skip.name, skip.kind, "skip", Counts(), 0.0, None, [], None, skip.reason)

    def line(self) -> str:
        fixed = [f"fixed {counted(len(self.fixed), 'file')}"] if self.fixed else []
        detail = ", ".join([self.kind, *self.counts.describe(), *fixed, f"{self.seconds:.1f}s"])
        listed = [f"  {path}" for path in self.fixed[:FAILURE_LINES]]
        match self.status:
            case "pass":
                return "\n".join([f"PASS {self.name} ({detail})", *listed])
            case "skip":
                return f"SKIP {self.name} ({self.kind}, {self.reason or 'nothing selected'})"
            case "fail":
                lines = [f"FAIL {self.name} ({detail}) log={self.log}"]
                return "\n".join([*lines, *listed, *(f"  {failure}" for failure in self.failures)])

    def as_json(self) -> dict:
        return {
            "name": self.name,
            "runner": self.kind,
            "status": self.status,
            "counts": {
                "passed": self.counts.passed,
                "failed": self.counts.failed,
                "skipped": self.counts.skipped,
            },
            "seconds": self.seconds,
            "log": self.log,
            "failures": self.failures,
            "command": self.command,
            "fixed": self.fixed,
        }


@dataclass
class Report:
    """One part's verdict; under --list, `planned` holds the commands it would run in place of outcomes."""

    logs: str | None
    notes: list[str]
    outcomes: list[Outcome] = field(default_factory=list)
    exit: int = 0
    planned: list[dict] | None = None

    def summary(self) -> dict[str, int]:
        statuses = [outcome.status for outcome in self.outcomes]
        return {
            "passed": statuses.count("pass"),
            "failed": statuses.count("fail"),
            "skipped": statuses.count("skip"),
        }

    def tally(self) -> str:
        summary = self.summary()
        return (
            f"verify: {summary['passed']} passed, {summary['failed']} failed, "
            f"{summary['skipped']} skipped"
        )

    def as_json(self) -> dict:
        if self.planned is not None:
            return {"suites": self.planned, "exit": self.exit, "notes": self.notes}
        return {
            "logs": self.logs,
            "suites": [outcome.as_json() for outcome in self.outcomes],
            "summary": self.summary(),
            "exit": self.exit,
            "notes": self.notes,
        }


def counted(count: int, noun: str) -> str:
    return f"{count} {noun if count == 1 else noun + 's'}"


def say(line: str) -> None:
    print(line, flush=True)


def warn(line: str) -> None:
    print(line, file=sys.stderr, flush=True)


def emit_json(value: dict) -> None:
    print(json.dumps(value, indent=2))
