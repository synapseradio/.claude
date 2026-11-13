"""What the person running `just test` sees: plain lines for pipes, live bars and a test tree for a terminal."""

from typing import Protocol, TextIO

import events
from events import Event

MARKS: dict[events.TestOutcome, str] = {"pass": "✓", "fail": "✗", "skip": "○"}
PATH_SEPARATOR = " \u203a "


class Display(Protocol):
    """`shows_waits` says whether the display draws a waiting suite; one that does not leaves the stderr line to the slot pool."""

    shows_waits: bool

    def note(self, text: str) -> None: ...
    def handle(self, event: Event) -> None: ...
    def close(self) -> None: ...


def display_for(stream: TextIO, *, verbose: bool, plain: bool) -> Display:
    if plain or not _is_terminal(stream):
        return PlainDisplay(stream, verbose=verbose)
    from live_display import live_display_on

    return live_display_on(stream, verbose=verbose)


def _is_terminal(stream: TextIO) -> bool:
    isatty = getattr(stream, "isatty", None)
    return bool(isatty and isatty())


def tree_lines(suite: str, status: events.TestOutcome, tests: list[events.TestEnded]) -> list[str]:
    """The suite, then each file in first-seen order, then each of its tests with its mark and time."""
    by_file: dict[str, list[events.TestEnded]] = {}
    for test in tests:
        by_file.setdefault(test.file, []).append(test)
    lines = [f"{MARKS[status]} {suite}"]
    for file, in_file in by_file.items():
        indent = "    " if file else "  "
        if file:
            lines.append(f"  {file}")
        for test in in_file:
            took = "" if test.seconds is None else f" ({test.seconds}s)"
            lines.append(f"{indent}{MARKS[test.outcome]} {test.name}{took}")
    return lines


def failure_line(test: events.TestEnded) -> str:
    where = [test.suite, *([test.file] if test.file else []), test.name]
    return f"{MARKS['fail']} {PATH_SEPARATOR.join(where)}"


class FinishedTests:
    """Finished tests per suite, kept only where a tree will print."""

    def __init__(self, *, enabled: bool) -> None:
        self._enabled = enabled
        self._by_suite: dict[str, list[events.TestEnded]] = {}

    def record(self, test: events.TestEnded) -> None:
        if self._enabled:
            self._by_suite.setdefault(test.suite, []).append(test)

    def tree(self, ended: events.SuiteEnded) -> list[str]:
        tests = self._by_suite.pop(ended.suite, [])
        return tree_lines(ended.suite, ended.status, tests) if self._enabled else []


class QuietDisplay:
    """Shows nothing, for a run whose stdout carries one JSON object."""

    shows_waits = False

    def note(self, text: str) -> None:
        pass

    def handle(self, event: Event) -> None:
        pass

    def close(self) -> None:
        pass


class PlainDisplay:
    """One line per fact, with no escape codes, byte for byte what the runner has always printed."""

    shows_waits = False

    def __init__(self, stream: TextIO, *, verbose: bool) -> None:
        self._stream = stream
        self._log = FinishedTests(enabled=verbose)

    def note(self, text: str) -> None:
        self._write(text)

    def handle(self, event: Event) -> None:
        match event:
            case events.SuiteWaiting(suite):
                self._write(f"verify: {suite} waiting for a slot")
            case events.TestEnded():
                self._log.record(event)
            case events.SuiteEnded():
                self._write(event.line)
                for line in self._log.tree(event):
                    self._write(line)

    def close(self) -> None:
        self._stream.flush()

    def _write(self, line: str) -> None:
        self._stream.write(f"{line}\n")
        self._stream.flush()
