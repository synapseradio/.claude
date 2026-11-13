#!/usr/bin/env python3
"""What the person running `just test` sees on screen and what pipes and hooks read.

The plain display prints one line per fact; the live display
draws one row per suite on a `rich` console. Live tests read the text a
recording console captured, never `rich` objects.
"""

import io
import pathlib
import re
import sys

import pytest
from rich.console import Console

VERIFY_DIR = pathlib.Path(__file__).resolve().parents[1] / "verify"

sys.path.insert(0, str(VERIFY_DIR))
import display  # noqa: E402  (path must be set before this import)
import events  # noqa: E402
import live_display  # noqa: E402

CURSOR_HIDE = "\x1b[?25l"
CURSOR_SHOW = "\x1b[?25h"
PASS_LINE = "PASS alpha  (12 passed)"
FAIL_LINE = "FAIL alpha  (1 failed, 2 passed)  log: /tmp/alpha.log"


@pytest.fixture(autouse=True)
def scratch_environment(tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "cache"))
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(tmp_path / "gitconfig"))


class Screen:
    """A recording terminal console and the raw bytes written to it."""

    def __init__(self) -> None:
        self.raw = io.StringIO()
        self.console = Console(
            file=self.raw,
            record=True,
            width=120,
            force_terminal=True,
            color_system=None,
            legacy_windows=False,
        )

    @property
    def text(self) -> str:
        return self.console.export_text(clear=False)


CONTROL_SEQUENCE = re.compile(r"\x1b\[([0-9;?]*)([A-Za-z])")


def terminal_after(written: str) -> list[str]:
    """The lines a terminal shows after receiving `written`: carriage return, line feed, cursor up, and erase line."""
    rows: list[list[str]] = [[]]
    row = col = 0
    position = 0
    while position < len(written):
        sequence = CONTROL_SEQUENCE.match(written, position)
        if sequence:
            arguments, final = sequence.groups()
            if final == "A":
                row = max(0, row - int(arguments or 1))
            elif final == "K" and arguments == "2":
                rows[row] = []
            position = sequence.end()
            continue
        char = written[position]
        position += 1
        if char == "\r":
            col = 0
        elif char == "\n":
            row, col = row + 1, 0
            while len(rows) <= row:
                rows.append([])
        else:
            line = rows[row]
            line.extend(" " * (col - len(line)))
            line[col : col + 1] = [char]
            col += 1
    return ["".join(line).rstrip() for line in rows]


@pytest.fixture
def screen() -> Screen:
    return Screen()


def live(screen: Screen, *, verbose: bool = False) -> display.Display:
    return live_display.LiveDisplay(screen.console, verbose=verbose)


def plain(stream: io.StringIO, *, verbose: bool = False) -> display.Display:
    return display.display_for(stream, verbose=verbose, plain=True)


def ended(
    suite: str,
    name: str,
    outcome: events.TestOutcome = "pass",
    *,
    file: str = "t/test_x.py",
    seconds: float | None = None,
) -> events.TestEnded:
    return events.TestEnded(suite=suite, file=file, name=name, outcome=outcome, seconds=seconds)


def feed(shown: display.Display, *sequence: events.Event) -> None:
    for event in sequence:
        shown.handle(event)


@pytest.fixture
def one_suite_run() -> list[events.Event]:
    return [
        events.SuiteWaiting("alpha"),
        events.SuiteStarted("alpha", workers=2),
        events.TestsCounted("alpha", total=2),
        ended("alpha", "test_one", seconds=0.5),
        ended("alpha", "test_two", seconds=1.5),
        events.SuiteEnded("alpha", "pass", PASS_LINE),
    ]


# plain display


def test_plain_display_prints_only_the_waiting_line_and_each_suite_line(
    one_suite_run: list[events.Event],
) -> None:
    stream = io.StringIO()
    shown = plain(stream)

    feed(shown, *one_suite_run)
    shown.close()

    assert stream.getvalue() == f"verify: alpha waiting for a slot\n{PASS_LINE}\n"


def test_plain_display_prints_the_failure_line_with_its_log_path_unchanged() -> None:
    stream = io.StringIO()
    shown = plain(stream)

    feed(shown, ended("alpha", "test_one", "fail"), events.SuiteEnded("alpha", "fail", FAIL_LINE))

    assert stream.getvalue() == f"{FAIL_LINE}\n"


def test_plain_display_prints_a_note_as_a_line() -> None:
    stream = io.StringIO()

    plain(stream).note("verify: 3 suites selected")

    assert stream.getvalue() == "verify: 3 suites selected\n"


def test_plain_display_keeps_a_suite_waiting_for_a_slot_on_its_own_line() -> None:
    stream = io.StringIO()

    feed(plain(stream), events.SuiteWaiting("a"), events.SuiteWaiting("b"))

    assert stream.getvalue() == "verify: a waiting for a slot\nverify: b waiting for a slot\n"


def test_plain_verbose_prints_the_suite_tree_after_its_line(
    one_suite_run: list[events.Event],
) -> None:
    stream = io.StringIO()
    shown = plain(stream, verbose=True)

    feed(shown, *one_suite_run)

    lines = stream.getvalue().splitlines()
    after_line = lines[lines.index(PASS_LINE) + 1 :]
    assert lines[:2] == ["verify: alpha waiting for a slot", PASS_LINE], (
        "the verdict line leads, unchanged"
    )
    assert any("✓" in line and "alpha" in line for line in after_line), (
        "tree names the suite with a pass mark"
    )
    assert any("t/test_x.py" in line for line in after_line), "tree names the file"
    assert any("✓" in line and "test_one" in line and "(0.5s)" in line for line in after_line), (
        "test with its time"
    )
    assert any("✓" in line and "test_two" in line and "(1.5s)" in line for line in after_line), (
        "second test with its time"
    )


def test_plain_verbose_marks_a_failed_test_in_the_tree_and_leaves_the_time_off_when_unknown() -> (
    None
):
    stream = io.StringIO()
    shown = plain(stream, verbose=True)

    feed(
        shown,
        ended("alpha", "test_broken", "fail", seconds=None),
        events.SuiteEnded("alpha", "fail", FAIL_LINE),
    )

    tree = stream.getvalue().splitlines()[1:]
    broken = [line for line in tree if "test_broken" in line]
    assert len(broken) == 1, "the failed test appears once in the tree"
    assert "✗" in broken[0], "a failed test carries the fail mark"
    assert "(" not in broken[0], "no time is shown where none is known"


def test_plain_verbose_marks_a_skipped_test_with_a_circle() -> None:
    stream = io.StringIO()

    feed(
        plain(stream, verbose=True),
        ended("alpha", "test_later", "skip"),
        events.SuiteEnded("alpha", "pass", PASS_LINE),
    )

    skipped = [line for line in stream.getvalue().splitlines() if "test_later" in line]
    assert len(skipped) == 1 and "○" in skipped[0], "a skipped test carries the skip mark"


def test_plain_verbose_lists_tests_without_a_file_directly_under_the_suite() -> None:
    stream = io.StringIO()

    feed(
        plain(stream, verbose=True),
        ended("alpha", "test_bare", file=""),
        events.SuiteEnded("alpha", "pass", PASS_LINE),
    )

    assert stream.getvalue().splitlines()[1:] == ["✓ alpha", "  ✓ test_bare"]


def test_plain_verbose_prints_the_tree_of_each_suite_with_only_its_own_tests() -> None:
    stream = io.StringIO()

    feed(
        plain(stream, verbose=True),
        ended("alpha", "test_a"),
        ended("beta", "test_b"),
        events.SuiteEnded("beta", "pass", "PASS beta"),
        events.SuiteEnded("alpha", "pass", PASS_LINE),
    )

    assert stream.getvalue().splitlines() == [
        "PASS beta",
        "✓ beta",
        "  t/test_x.py",
        "    ✓ test_b",
        PASS_LINE,
        "✓ alpha",
        "  t/test_x.py",
        "    ✓ test_a",
    ]


def test_plain_verbose_prints_nothing_for_a_suite_still_running() -> None:
    stream = io.StringIO()

    feed(
        plain(stream, verbose=True),
        events.SuiteStarted("alpha", workers=1),
        events.TestsCounted("alpha", 1),
        ended("alpha", "test_one"),
    )

    assert stream.getvalue() == ""


def test_plain_without_verbose_never_prints_the_tree(one_suite_run: list[events.Event]) -> None:
    stream = io.StringIO()

    feed(plain(stream), *one_suite_run)

    assert "test_one" not in stream.getvalue()


# display_for


def test_display_for_a_stream_that_is_not_a_terminal_prints_plain_lines(
    one_suite_run: list[events.Event],
) -> None:
    stream = io.StringIO()
    shown = display.display_for(stream, verbose=False, plain=False)

    feed(shown, *one_suite_run)
    shown.close()

    assert stream.getvalue() == f"verify: alpha waiting for a slot\n{PASS_LINE}\n"


def test_display_for_plain_requested_prints_plain_lines_on_a_terminal(
    one_suite_run: list[events.Event],
) -> None:
    class Terminal(io.StringIO):
        def isatty(self) -> bool:
            return True

    stream = Terminal()
    shown = display.display_for(stream, verbose=False, plain=True)

    feed(shown, *one_suite_run)

    assert stream.getvalue() == f"verify: alpha waiting for a slot\n{PASS_LINE}\n"


def test_display_for_a_terminal_draws_live_rows_and_not_plain_lines() -> None:
    class Terminal(io.StringIO):
        def isatty(self) -> bool:
            return True

    stream = Terminal()
    shown = display.display_for(stream, verbose=False, plain=False)

    feed(shown, events.SuiteWaiting("alpha"))
    shown.close()

    assert "verify: alpha waiting for a slot" not in stream.getvalue(), (
        "the plain waiting line stays off a terminal"
    )
    assert "waiting for a slot" in stream.getvalue(), (
        "the live row still tells the suite is waiting"
    )


# live display


def test_live_row_shows_how_many_tests_finished_of_the_total(screen: Screen) -> None:
    shown = live(screen)

    feed(
        shown,
        events.SuiteStarted("alpha", 2),
        events.TestsCounted("alpha", 10),
        ended("alpha", "t1"),
        ended("alpha", "t2"),
        ended("alpha", "t3"),
    )
    shown.close()

    assert "alpha" in screen.text, "the row names the suite"
    assert "3/10" in screen.text, "three finished of ten"


def test_live_row_counts_only_the_tests_that_have_ended(screen: Screen) -> None:
    shown = live(screen)

    feed(
        shown,
        events.SuiteStarted("alpha", 2),
        events.TestsCounted("alpha", 10),
        ended("alpha", "t1"),
        ended("alpha", "t2"),
    )
    shown.close()

    assert "2/10" in screen.text, "two finished of ten"
    assert "3/10" not in screen.text, "no third test has ended"


def test_live_rows_count_each_suite_on_its_own(screen: Screen) -> None:
    shown = live(screen)

    feed(
        shown,
        events.SuiteStarted("alpha", 1),
        events.SuiteStarted("beta", 1),
        events.TestsCounted("alpha", 4),
        events.TestsCounted("beta", 7),
        ended("alpha", "t1"),
        ended("beta", "t1"),
        ended("beta", "t2"),
    )
    shown.close()

    assert "1/4" in screen.text, "alpha has one of four"
    assert "2/7" in screen.text, "beta has two of seven"


def test_live_row_of_a_suite_without_a_free_slot_reads_waiting_for_a_slot(screen: Screen) -> None:
    shown = live(screen)

    feed(shown, events.SuiteWaiting("alpha"))
    shown.close()

    assert "alpha" in screen.text, "the waiting suite has a row"
    assert "waiting for a slot" in screen.text, "the row says why it has not started"


def test_live_rows_keep_the_order_suites_were_first_seen(screen: Screen) -> None:
    shown = live(screen)

    feed(
        shown,
        events.SuiteWaiting("zeta"),
        events.SuiteWaiting("alpha"),
        events.SuiteStarted("alpha", 1),
        events.SuiteStarted("zeta", 1),
    )
    shown.close()

    assert screen.text.index("zeta") < screen.text.index("alpha"), (
        "zeta was seen first and stays above alpha"
    )


def test_live_failed_test_prints_its_suite_file_and_name(screen: Screen) -> None:
    shown = live(screen)

    feed(
        shown,
        events.SuiteStarted("alpha", 1),
        events.TestsCounted("alpha", 3),
        ended("alpha", "test_it_breaks", "fail", file="t/test_x.py"),
    )
    shown.close()

    assert "✗ alpha \u203a t/test_x.py \u203a test_it_breaks" in screen.text


def test_live_failed_test_name_prints_verbatim_when_it_looks_like_markup(screen: Screen) -> None:
    shown = live(screen)

    feed(shown, events.SuiteStarted("alpha", 1), ended("alpha", "test_it[red]x[/red]", "fail"))
    shown.close()

    assert "✗ alpha \u203a t/test_x.py \u203a test_it[red]x[/red]" in screen.text


def test_live_passing_test_prints_no_line_of_its_own(screen: Screen) -> None:
    shown = live(screen)

    feed(
        shown,
        events.SuiteStarted("alpha", 1),
        events.TestsCounted("alpha", 3),
        ended("alpha", "test_it_works"),
    )
    shown.close()

    assert "test_it_works" not in screen.text


def test_live_failed_suite_prints_its_line_with_the_log_path(screen: Screen) -> None:
    shown = live(screen)

    feed(shown, events.SuiteStarted("alpha", 1), events.SuiteEnded("alpha", "fail", FAIL_LINE))
    shown.close()

    assert FAIL_LINE in screen.text


def test_live_note_prints_its_text(screen: Screen) -> None:
    shown = live(screen)

    shown.note("verify: 3 suites selected")
    shown.close()

    assert "verify: 3 suites selected" in screen.text


def test_live_verbose_prints_the_tree_of_a_suite_when_it_ends(
    screen: Screen, one_suite_run: list[events.Event]
) -> None:
    shown = live(screen, verbose=True)

    feed(shown, *one_suite_run)
    shown.close()

    lines = screen.text.splitlines()
    assert any(line.strip().startswith("✓ alpha") for line in lines), (
        "tree opens on the suite with a pass mark"
    )
    assert any("t/test_x.py" in line for line in lines), "tree names the file"
    assert any("✓" in line and "test_one" in line and "(0.5s)" in line for line in lines), (
        "first test with its time"
    )
    assert any("✓" in line and "test_two" in line and "(1.5s)" in line for line in lines), (
        "second test with its time"
    )


def test_live_without_verbose_prints_no_tree(
    screen: Screen, one_suite_run: list[events.Event]
) -> None:
    shown = live(screen)

    feed(shown, *one_suite_run)
    shown.close()

    assert "test_one" not in screen.text
    assert "t/test_x.py" not in screen.text


def test_live_close_shows_the_cursor_again(screen: Screen) -> None:
    shown = live(screen)
    feed(
        shown,
        events.SuiteStarted("alpha", 1),
        events.TestsCounted("alpha", 2),
        ended("alpha", "t1"),
    )

    shown.close()

    written = screen.raw.getvalue()
    assert CURSOR_HIDE in written, "the bars hid the cursor while they ran"
    assert written.rfind(CURSOR_SHOW) > written.rfind(CURSOR_HIDE), (
        "the cursor is visible again after close"
    )


def test_live_close_leaves_nothing_drawn_by_a_later_note(screen: Screen) -> None:
    shown = live(screen)
    feed(
        shown,
        events.SuiteStarted("alpha", 1),
        events.TestsCounted("alpha", 2),
        ended("alpha", "t1"),
    )
    shown.close()
    before = screen.raw.getvalue()

    screen.console.print("after the run")

    after = screen.raw.getvalue()[len(before) :]
    assert after == "after the run\n", (
        "a line printed after close is not redrawn over or followed by bars"
    )


def test_live_close_without_any_event_leaves_the_screen_clean(screen: Screen) -> None:
    live(screen).close()

    assert screen.text.strip() == ""
    assert CURSOR_HIDE not in screen.raw.getvalue() or screen.raw.getvalue().rfind(
        CURSOR_SHOW
    ) > screen.raw.getvalue().rfind(CURSOR_HIDE)


def test_live_close_with_a_suite_unfinished_leaves_no_bar_on_the_terminal(screen: Screen) -> None:
    shown = live(screen)
    feed(
        shown,
        events.SuiteStarted("alpha", 1),
        events.TestsCounted("alpha", 10),
        ended("alpha", "t1"),
        ended("alpha", "t2"),
        ended("alpha", "t3"),
    )

    shown.close()

    shown_lines = terminal_after(screen.raw.getvalue())
    assert not any("alpha" in line or "/10" in line for line in shown_lines), (
        "no row of the cut-short suite remains"
    )


def test_live_close_with_a_suite_waiting_leaves_no_row_on_the_terminal(screen: Screen) -> None:
    shown = live(screen)
    feed(shown, events.SuiteWaiting("alpha"))

    shown.close()

    assert not any("waiting for a slot" in line for line in terminal_after(screen.raw.getvalue()))


def test_live_close_with_a_suite_unfinished_keeps_the_text_printed_above_the_bars(
    screen: Screen,
) -> None:
    shown = live(screen)
    feed(
        shown,
        events.SuiteStarted("alpha", 1),
        events.TestsCounted("alpha", 3),
        ended("alpha", "test_it_breaks", "fail"),
    )
    shown.note("verify: interrupted")

    shown.close()

    shown_lines = terminal_after(screen.raw.getvalue())
    assert "\u2717 alpha \u203a t/test_x.py \u203a test_it_breaks" in shown_lines
    assert "verify: interrupted" in shown_lines
    assert not any("0/3" in line or "1/3" in line for line in shown_lines)


def test_live_close_after_every_suite_ended_keeps_the_finished_rows(
    screen: Screen, one_suite_run: list[events.Event]
) -> None:
    shown = live(screen)
    feed(shown, *one_suite_run)

    shown.close()

    assert any("alpha" in line and "2/2" in line for line in terminal_after(screen.raw.getvalue()))
