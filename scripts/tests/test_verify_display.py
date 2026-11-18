#!/usr/bin/env -S uv run --frozen
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


def test_plain_verbose_marks_each_outcome_and_leaves_the_time_off_when_unknown() -> None:
    stream = io.StringIO()

    feed(
        plain(stream, verbose=True),
        ended("alpha", "test_fine"),
        ended("alpha", "test_broken", "fail", seconds=None),
        ended("alpha", "test_later", "skip"),
        events.SuiteEnded("alpha", "fail", FAIL_LINE),
    )

    tree = {
        name: [line for line in stream.getvalue().splitlines()[1:] if name in line]
        for name in ("test_fine", "test_broken", "test_later")
    }
    assert all(len(lines) == 1 for lines in tree.values()), "each test appears once in the tree"
    assert "✓" in tree["test_fine"][0], "a passed test carries the pass mark"
    assert "✗" in tree["test_broken"][0], "a failed test carries the fail mark"
    assert "○" in tree["test_later"][0], "a skipped test carries the skip mark"
    assert "(" not in tree["test_broken"][0], "no time is shown where none is known"


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


# display_for


class Terminal(io.StringIO):
    def isatty(self) -> bool:
        return True


@pytest.mark.parametrize(
    ("stream_factory", "plain_requested", "drawn_plain"),
    [
        pytest.param(io.StringIO, False, True, id="a stream that is not a terminal"),
        pytest.param(Terminal, True, True, id="plain requested on a terminal"),
        pytest.param(Terminal, False, False, id="a terminal"),
    ],
)
def test_display_for_picks_plain_lines_off_a_terminal_or_when_asked_and_live_rows_otherwise(
    stream_factory, plain_requested, drawn_plain
) -> None:
    stream = stream_factory()
    shown = display.display_for(stream, verbose=False, plain=plain_requested)

    feed(shown, events.SuiteWaiting("alpha"))
    shown.close()

    waiting_line = "verify: alpha waiting for a slot"
    assert (waiting_line in stream.getvalue()) is drawn_plain, (
        "the plain waiting line belongs to plain output alone"
    )
    assert "waiting for a slot" in stream.getvalue(), "either way the suite is shown waiting"


# live display


def test_live_rows_count_the_ended_tests_of_each_suite_on_its_own(screen: Screen) -> None:
    shown = live(screen)

    feed(
        shown,
        events.SuiteStarted("alpha", 1),
        events.SuiteStarted("beta", 1),
        events.TestsCounted("alpha", 10),
        events.TestsCounted("beta", 7),
        ended("alpha", "t1"),
        ended("alpha", "t2"),
        ended("alpha", "t3"),
        ended("beta", "t1"),
        ended("beta", "t2"),
    )
    shown.close()

    assert "3/10" in screen.text, "alpha has three of ten"
    assert "2/7" in screen.text, "beta has two of seven"
    assert "2/10" not in screen.text and "3/7" not in screen.text, "each suite counts alone"


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


@pytest.mark.parametrize("name", ["test_it_breaks", "test_it[red]x[/red]"])
def test_live_failed_test_prints_its_suite_file_and_name_verbatim(screen: Screen, name) -> None:
    shown = live(screen)

    feed(
        shown,
        events.SuiteStarted("alpha", 1),
        events.TestsCounted("alpha", 3),
        ended("alpha", name, "fail", file="t/test_x.py"),
    )
    shown.close()

    assert f"✗ alpha \u203a t/test_x.py \u203a {name}" in screen.text


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


def test_live_close_shows_the_cursor_again_and_later_lines_print_cleanly(screen: Screen) -> None:
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

    assert CURSOR_HIDE in before, "the bars hid the cursor while they ran"
    assert before.rfind(CURSOR_SHOW) > before.rfind(CURSOR_HIDE), (
        "the cursor is visible again after close"
    )
    assert screen.raw.getvalue()[len(before) :] == "after the run\n", (
        "a line printed after close is not redrawn over or followed by bars"
    )


@pytest.mark.parametrize(
    "unfinished",
    [
        pytest.param(
            [
                events.SuiteStarted("alpha", 1),
                events.TestsCounted("alpha", 10),
                ended("alpha", "t1"),
                ended("alpha", "t2"),
                ended("alpha", "t3"),
            ],
            id="a suite part-way through",
        ),
        pytest.param([events.SuiteWaiting("alpha")], id="a suite waiting for a slot"),
    ],
)
def test_live_close_with_a_suite_unfinished_leaves_no_row_on_the_terminal(
    screen: Screen, unfinished: list[events.Event]
) -> None:
    shown = live(screen)
    feed(shown, *unfinished)

    shown.close()

    shown_lines = terminal_after(screen.raw.getvalue())
    assert not any("alpha" in line or "/10" in line or "waiting" in line for line in shown_lines), (
        "no row of the cut-short suite remains"
    )


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
