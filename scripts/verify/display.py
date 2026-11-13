"""What the person running `just test` sees: plain lines for pipes, live bars and a test tree for a terminal."""

from collections.abc import Iterable
from typing import Protocol, TextIO

import events
from events import Event
from rich.console import Console, RenderableType
from rich.progress import (
    BarColumn,
    Progress,
    ProgressColumn,
    Task,
    TaskID,
    TextColumn,
    TimeElapsedColumn,
)
from rich.text import Text

MARKS: dict[events.TestOutcome, str] = {"pass": "✓", "fail": "✗", "skip": "○"}
PATH_SEPARATOR = " \u203a "
WAITING_TEXT = "waiting for a slot"
REFRESHES_PER_SECOND = 4


class Display(Protocol):
    def note(self, text: str) -> None: ...
    def handle(self, event: Event) -> None: ...
    def close(self) -> None: ...


def display_for(stream: TextIO, *, verbose: bool, plain: bool) -> Display:
    if plain or not _is_terminal(stream):
        return PlainDisplay(stream, verbose=verbose)
    return LiveDisplay(Console(file=stream), verbose=verbose)


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


class PlainDisplay:
    """One line per fact, with no escape codes, byte for byte what the runner has always printed."""

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


class _WaitingOrBar(ProgressColumn):
    def __init__(self) -> None:
        super().__init__()
        self._bar = BarColumn(bar_width=30)

    def render(self, task: Task) -> RenderableType:
        if task.fields["state"] == "waiting":
            return Text(WAITING_TEXT, style="dim")
        return self._bar.render(task)


class _Count(ProgressColumn):
    def render(self, task: Task) -> Text:
        if task.fields["state"] == "waiting":
            return Text("")
        total = task.fields["expected"]
        return Text(
            f"{int(task.completed)}/{'?' if total is None else total}", style="progress.download"
        )


class _Elapsed(ProgressColumn):
    def __init__(self) -> None:
        super().__init__()
        self._elapsed = TimeElapsedColumn()

    def render(self, task: Task) -> Text:
        if task.fields["state"] == "waiting":
            return Text("")
        return self._elapsed.render(task)


class _BarsAboveABlankLine(Progress):
    """Ends every frame on its own empty line, so text printed above the bars starts a fresh line."""

    def get_renderables(self) -> Iterable[RenderableType]:
        yield from super().get_renderables()
        yield Text("")


class LiveDisplay:
    """One row per suite on a refreshing region, with failures and finished trees printed above it.

    The region refreshes on rich's own thread so elapsed times keep moving while a suite is
    quiet; rich guards its task table with a lock, and every print goes through the live console.
    """

    def __init__(self, console: Console, *, verbose: bool = False) -> None:
        self._console = console
        self._finished = FinishedTests(enabled=verbose)
        self._rows: dict[str, TaskID] = {}
        self._progress = _BarsAboveABlankLine(
            TextColumn("{task.description}", markup=False),
            _WaitingOrBar(),
            _Count(),
            _Elapsed(),
            TextColumn("{task.fields[mark]}"),
            console=console,
            refresh_per_second=REFRESHES_PER_SECOND,
        )

    def note(self, text: str) -> None:
        self._print(text)

    def handle(self, event: Event) -> None:
        match event:
            case events.SuiteWaiting(suite):
                self._row(suite)
            case events.SuiteStarted(suite):
                self._start(suite)
            case events.TestsCounted(suite, total):
                self._progress.update(self._row(suite), total=max(total, 1), expected=total)
            case events.TestEnded():
                self._finished.record(event)
                self._progress.advance(self._start(event.suite))
                if event.outcome == "fail":
                    self._print(failure_line(event))
            case events.SuiteEnded():
                self._end(event)

    def close(self) -> None:
        self._progress.stop()

    def _row(self, suite: str) -> TaskID:
        if suite not in self._rows:
            self._rows[suite] = self._progress.add_task(
                suite, start=False, total=None, state="waiting", expected=None, mark=""
            )
            self._progress.start()
        return self._rows[suite]

    def _start(self, suite: str) -> TaskID:
        row = self._row(suite)
        if self._progress.tasks[row].fields["state"] == "waiting":
            self._progress.update(row, state="running")
            self._progress.start_task(row)
        return row

    def _end(self, ended: events.SuiteEnded) -> None:
        row = self._start(ended.suite)
        done = int(self._progress.tasks[row].completed)
        known = self._progress.tasks[row].fields["expected"]
        self._progress.update(
            row,
            state="ended",
            mark=MARKS[ended.status],
            expected=done if known is None else known,
            total=max(done, known or 0, 1),
        )
        self._progress.stop_task(row)
        if ended.status == "fail":
            self._print(ended.line)
        self._print("\n".join(self._finished.tree(ended)))

    def _print(self, text: str) -> None:
        if text:
            self._console.print(text, markup=False, highlight=False, emoji=False, soft_wrap=True)
