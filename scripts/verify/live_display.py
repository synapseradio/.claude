"""The live view for a terminal: one refreshing bar per suite, with failures and finished trees printed above.

It lives apart from display.py so that a run with no terminal never imports rich.
"""

from collections.abc import Iterable
from typing import TextIO

import events
from display import MARKS, FinishedTests, failure_line
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

WAITING_TEXT = "waiting for a slot"
REFRESHES_PER_SECOND = 4


def live_display_on(stream: TextIO, *, verbose: bool) -> LiveDisplay:
    return LiveDisplay(Console(file=stream), verbose=verbose)


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

    shows_waits = True

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
        self._progress.live.transient = any(
            task.fields["state"] != "ended" for task in self._progress.tasks
        )
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
