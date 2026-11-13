#!/usr/bin/env python3
"""The machine-wide slot pool that caps how many workers every worktree's runs start.

The pool is `$XDG_CACHE_HOME/claude-verify/slots/slot-0..N-1` with N from
VERIFY_SLOTS, each slot an flock'd file. A suite takes free slots without
blocking up to the workers it wants; holding none, it announces on stderr that
it waits and blocks on one. It runs with k held slots as pytest `-n k` or bats
`--jobs k`, either flag left out at one. `--jobs N` caps the workers a suite
wants; `--serial` runs one suite at a time.

Contention comes from a child process that holds slot flocks and releases
them only when the test writes to its stdin, writing a marker file first, so
a stub that records the marker as present ran after the release.
"""

import fcntl

import pytest
from verify_fixtures import RUN_TIMEOUT, Sandbox, pair, read_until


@pytest.fixture
def sb(tmp_path) -> Sandbox:
    return Sandbox(tmp_path)


def test_a_suite_finding_every_slot_held_waits_then_runs_once_they_free(sb) -> None:
    holder = sb.hold(0, 1)
    process = sb.popen("test", "shell/tests/one.bats", extra_env={"VERIFY_SLOTS": "2"})
    try:
        waiting, seen = read_until(process.stderr, b"waiting for a slot")
        assert waiting, (
            "with both slots held the run announces that it waits before blocking; "
            f"stderr so far: {seen.decode(errors='replace')}"
        )
        assert sb.calls() == [], "no runner starts while every slot is held"

        holder.release()
        _out, err = process.communicate(timeout=RUN_TIMEOUT)
    finally:
        holder.kill()
        if process.poll() is None:
            process.kill()
            process.wait(timeout=RUN_TIMEOUT)

    assert process.returncode == 0, f"exit {process.returncode}: {err.decode(errors='replace')}"
    calls = sb.calls("bats")
    assert len(calls) == 1, f"bats ran {len(calls)} times"
    assert calls[0]["released"], "bats started before the holder released its slots"
    assert "--jobs" not in calls[0]["args"], (
        f"one test file wants one worker, and bats takes no --jobs at one: {calls[0]['args']}"
    )


def test_a_suite_runs_with_as_many_workers_as_slots_it_could_take(sb) -> None:
    holder = sb.hold(0)
    try:
        result = sb.run("test", "pkg_a", extra_env={"VERIFY_SLOTS": "3"})
    finally:
        holder.kill()

    assert result.returncode == 0, f"exit {result.returncode}: {result.stderr}"
    args = sb.call_for("uv", "pkg_a")["args"]
    assert pair(args, "-n", "2"), (
        f"three test files want three workers, one of three slots is held, so pytest gets -n 2: {args}"
    )


def test_a_suite_takes_no_more_slots_than_it_has_test_files(sb) -> None:
    result = sb.run("test", "pkg_a", extra_env={"VERIFY_SLOTS": "8"})

    assert result.returncode == 0, f"exit {result.returncode}: {result.stderr}"
    args = sb.call_for("uv", "pkg_a")["args"]
    assert pair(args, "-n", "3"), f"pkg_a/tests holds three test files: {args}"


def test_a_pytest_suite_holding_one_slot_runs_without_n(sb) -> None:
    result = sb.run("test", "pkg_a/tests/test_a2.py", extra_env={"VERIFY_SLOTS": "8"})

    assert result.returncode == 0, f"exit {result.returncode}: {result.stderr}"
    args = sb.call_for("uv", "pkg_a")["args"]
    assert "-n" not in args, f"one test file wants one worker, run without xdist: {args}"


def test_jobs_caps_the_workers_a_suite_takes(sb) -> None:
    result = sb.run("test", "pkg_a", "--jobs", "2", extra_env={"VERIFY_SLOTS": "8"})

    assert result.returncode == 0, f"exit {result.returncode}: {result.stderr}"
    args = sb.call_for("uv", "pkg_a")["args"]
    assert pair(args, "-n", "2"), f"three test files, capped at two workers: {args}"


def test_jobs_one_runs_pytest_without_n(sb) -> None:
    result = sb.run("test", "pkg_a", "--jobs", "1", extra_env={"VERIFY_SLOTS": "8"})

    assert result.returncode == 0, f"exit {result.returncode}: {result.stderr}"
    args = sb.call_for("uv", "pkg_a")["args"]
    assert "-n" not in args, args


def test_serial_starts_each_suite_after_the_one_before_exits(sb) -> None:
    result = sb.run("test", "pkg_a", "pkg_b", "shell", "--serial")

    assert result.returncode == 0, f"exit {result.returncode}: {result.stderr}"
    events = sb.events()
    starts = [event for event in events if event["event"] == "start"]
    assert len(starts) == 3, [event["args"] for event in starts]
    running = set()
    for event in events:
        if event["event"] == "start":
            assert not running, f"{event['prog']} {event['args']} started while {running} still ran"
            running.add(event["pid"])
        else:
            running.discard(event["pid"])


def test_a_bats_suite_takes_its_held_slots_as_jobs(sb) -> None:
    result = sb.run("test", "shell", extra_env={"VERIFY_SLOTS": "8"})

    assert result.returncode == 0, f"exit {result.returncode}: {result.stderr}"
    args = sb.calls("bats")[0]["args"]
    assert pair(args, "--jobs", "2"), f"shell/tests holds two bats files: {args}"


def test_the_pool_sits_under_home_cache_when_xdg_cache_home_is_unset(sb) -> None:
    """https://specifications.freedesktop.org/basedir-spec/latest/ names $HOME/.cache as the default."""
    del sb.env["XDG_CACHE_HOME"]

    result = sb.run("test", "pkg_b", extra_env={"VERIFY_SLOTS": "2"})

    assert result.returncode == 0, f"exit {result.returncode}: {result.stderr}"
    pool = sb.home / ".cache" / "claude-verify" / "slots"
    assert pool.is_dir() and any(pool.glob("slot-*")), f"the run took no slot under {pool}"
    assert not sb.slot_dir.exists(), f"nothing set XDG_CACHE_HOME, yet {sb.slot_dir} was written"


def test_every_slot_is_free_once_the_run_ends(sb) -> None:
    result = sb.run("test", "pkg_a", extra_env={"VERIFY_SLOTS": "3"})

    assert result.returncode == 0, f"exit {result.returncode}: {result.stderr}"
    for index in range(3):
        slot = sb.slot(index)
        assert slot.is_file(), f"the pool keeps its slots at {sb.slot_dir}"
        with open(slot, "a") as handle:
            try:
                fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                pytest.fail(f"{slot.name} is still held after the run exited")
