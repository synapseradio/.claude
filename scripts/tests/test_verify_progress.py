#!/usr/bin/env python3
"""How `progress.parser_for` turns one framework output line at a time into events.

Each sample under `progress_samples/` is the real output of a three-test scratch
suite run with the flags `progress.extra_argv` supplies. The pytest sample, the
pytest-xdist sample, and the bats sample hold a pass, a failure, and a skip; the
mod sample holds two passes and a failure. Expected totals, names, outcomes, and
durations are read off those samples; the contract is `TestsCounted` once the
total is known and one `TestEnded` per finished test.
"""

import importlib
import pathlib
import sys
from typing import Protocol

import pytest

VERIFY_DIR = pathlib.Path(__file__).resolve().parents[1] / "verify"
SAMPLES = pathlib.Path(__file__).resolve().parent / "progress_samples"

sys.path.insert(0, str(VERIFY_DIR))
import events  # noqa: E402  (path must be set before this import)

SUITE = "sample"
PYTEST_FILE = "tests/test_sample.py"
MOD_ROOT = "features/mods/context-gauge"
MOD_FILE = f"{MOD_ROOT}/tests/sample.test.ts"


class Feeder(Protocol):
    def feed(self, line: str) -> list[events.Event]: ...


def parser_for(kind: str, root: str) -> Feeder:
    return importlib.import_module("progress").parser_for(kind, SUITE, root)


def extra_argv(kind: str) -> list[str]:
    return importlib.import_module("progress").extra_argv(kind)


def sample_lines(name: str) -> list[str]:
    return (SAMPLES / name).read_text().splitlines()


def feed_sample(kind: str, name: str) -> list[events.Event]:
    parser = parser_for(kind, MOD_ROOT if kind == "mod" else "")
    found: list[events.Event] = []
    for line in sample_lines(name):
        found += parser.feed(line)
    return found


def ended(
    file: str, name: str, outcome: events.TestOutcome, seconds: float | None
) -> events.TestEnded:
    return events.TestEnded(SUITE, file, name, outcome, seconds)


PYTEST_ENDED = [
    ended(PYTEST_FILE, "test_adds_numbers", "pass", None),
    ended(PYTEST_FILE, "test_rejects_wrong_sum", "fail", None),
    ended(PYTEST_FILE, "test_skipped_case", "skip", None),
]

XDIST_ENDED = [PYTEST_ENDED[0], PYTEST_ENDED[2], PYTEST_ENDED[1]]

BATS_ENDED = [
    ended("", "adds numbers", "pass", 0.002),
    ended("", "rejects wrong sum", "fail", 0.001),
    ended("", "skipped case", "skip", 0.002),
]

MOD_ENDED = [
    ended(MOD_FILE, "sums > adds numbers", "pass", 0.00121),
    ended(MOD_FILE, "sums > rejects wrong sum", "fail", 0.00021),
    ended(MOD_FILE, "sums > subtracts numbers", "pass", 0.00014),
]

SAMPLE_CASES = {
    "pytest": ("pytest", "pytest.txt", PYTEST_ENDED),
    "pytest under xdist": ("pytest", "pytest-xdist.txt", XDIST_ENDED),
    "bats": ("bats", "bats-tap-timing.txt", BATS_ENDED),
    "mod": ("mod", "plugin-test.txt", MOD_ENDED),
}

UNKNOWN_LINES = {
    "pytest": [
        "",
        "plain text no framework prints",
        "=================================== FAILURES ===================================",
        "E       assert (1 + 1) == 3",
        "tests/test_sample.py:9: AssertionError",
        "scheduling tests via LoadScheduling",
        "tests/test_sample.py::test_adds_numbers ",
        "FAILED tests/test_sample.py::test_rejects_wrong_sum - assert (1 + 1) == 3",
        "==================== 1 failed, 1 passed, 1 skipped in 0.02s ====================",
    ],
    "bats": [
        "",
        "plain text no framework prints",
        "# (in test file tests/sample.bats, line 6)",
        "#   `[ $((1 + 1)) -eq 3 ]' failed",
        "ok",
        "not ok",
    ],
    "mod": [
        "",
        "plain text no framework prints",
        "  AssertionError: expect(received).toBe()",
        "  Expected: 3",
        " 2 pass",
        " 1 fail",
        "(pass)",
    ],
}


@pytest.mark.parametrize("case", SAMPLE_CASES)
def test_a_sample_yields_its_count_once_then_one_test_ended_per_test_in_the_order_it_printed(
    case: str,
) -> None:
    kind, name, expected = SAMPLE_CASES[case]

    found = feed_sample(kind, name)

    assert [e for e in found if isinstance(e, events.TestsCounted)] == [
        events.TestsCounted(SUITE, 3)
    ], f"{case}: expected one count of 3"
    assert [e for e in found if isinstance(e, events.TestEnded)] == expected, (
        f"{case}: expected {len(expected)} finished tests"
    )
    assert [e for e in found if not isinstance(e, events.TestsCounted | events.TestEnded)] == [], (
        f"{case}: a line produced an event of another kind"
    )


@pytest.mark.parametrize("kind", UNKNOWN_LINES)
def test_a_line_that_is_no_framework_result_returns_no_events(kind: str) -> None:
    parser = parser_for(kind, MOD_ROOT if kind == "mod" else "")

    produced = {line: parser.feed(line) for line in UNKNOWN_LINES[kind]}

    assert {line: found for line, found in produced.items() if found} == {}, (
        f"{kind}: these lines produced events"
    )


def test_a_non_empty_root_is_joined_onto_a_pytest_path() -> None:
    line = "tests/test_sample.py::test_adds_numbers PASSED   [ 33%]"

    assert parser_for("pytest", "features/plugins/x").feed(line) == [
        ended("features/plugins/x/tests/test_sample.py", "test_adds_numbers", "pass", None)
    ]


@pytest.mark.parametrize(
    ("kind", "argv"),
    [("pytest", ["-v"]), ("bats", ["--timing"]), ("mod", [])],
)
def test_extra_argv_asks_each_framework_for_one_line_per_finished_test(
    kind: str, argv: list[str]
) -> None:
    assert extra_argv(kind) == argv
