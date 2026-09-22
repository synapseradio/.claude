"""Part k exits only after part k-1's process is gone.

The harness appends each hook's context in the order the hooks exit, so a
part that waits for its predecessor's process lands after it. These tests
stand a process of their own in for the predecessor, so the test decides
when it exits, and point every slot at a temporary state directory.
"""

import json
import os
import pathlib
import subprocess
import sys
import threading
import time

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]
HOOK = PLUGIN_ROOT / "hooks" / "deliver.py"

sys.path.insert(0, str(PLUGIN_ROOT / "lib"))

from rulesets import ordering, resolve  # noqa: E402  (path must be set before this import)

PAYLOAD = json.dumps(
    {"hook_event_name": "SessionStart", "session_id": "s1", "model": "claude-haiku-4-5"}
)


def hold_open(slots, part=1):
    """A process registered as `part` that lives until the test closes its stdin."""

    script = (
        "import pathlib, sys\n"
        f"sys.path.insert(0, {str(PLUGIN_ROOT / 'lib')!r})\n"
        "from rulesets import ordering\n"
        f"ordering.register(pathlib.Path({str(slots)!r}), {part})\n"
        "print('registered', flush=True)\n"
        "sys.stdin.read()\n"
    )
    process = subprocess.Popen(
        [sys.executable, "-c", script], stdin=subprocess.PIPE, stdout=subprocess.PIPE
    )
    assert process.stdout.readline() == b"registered\n"
    return process


def build_two_part_corpus(tmp_path):
    """A corpus whose haiku tier packs into two parts."""

    root = tmp_path / "corpus"
    resolve.scaffold(root)
    for stem in ("alpha", "beta"):
        body = f"Body {stem}. " + "x" * 5000 + "\n"
        (root / "default" / f"{stem}.md").write_text(body, encoding="utf-8")
    return root


class TestWaitForPredecessor:
    def test_part_one_waits_for_nothing(self, tmp_path):
        slots = ordering.slot_dir(tmp_path, PAYLOAD)

        assert ordering.wait_for_predecessor(slots, 1, deadline=0.0) is True

    def test_a_part_waits_while_its_predecessor_lives_and_returns_once_it_is_gone(self, tmp_path):
        slots = ordering.slot_dir(tmp_path, PAYLOAD)
        predecessor = hold_open(slots)
        results = []
        waiter = threading.Thread(
            target=lambda: results.append(ordering.wait_for_predecessor(slots, 2, deadline=10.0))
        )

        waiter.start()
        waiter.join(0.3)
        still_waiting = waiter.is_alive()
        predecessor.communicate(b"")
        waiter.join(5.0)

        assert still_waiting, "part 2 returned while part 1's process was still running"
        assert results == [True], "part 2 did not return once part 1's process was gone"

    def test_a_part_returns_at_once_when_its_predecessor_already_exited(self, tmp_path):
        slots = ordering.slot_dir(tmp_path, PAYLOAD)
        hold_open(slots).communicate(b"")

        started = time.monotonic()
        waited = ordering.wait_for_predecessor(slots, 2, deadline=5.0)

        assert waited is True
        assert time.monotonic() - started < 1.0, "an exited predecessor held part 2 back"

    def test_a_part_gives_up_at_the_deadline_when_its_predecessor_never_registers(self, tmp_path):
        slots = ordering.slot_dir(tmp_path, PAYLOAD)

        started = time.monotonic()
        waited = ordering.wait_for_predecessor(slots, 2, deadline=0.2)

        assert waited is False, "a missing predecessor must read as a timeout, not an exit"
        assert 0.2 <= time.monotonic() - started < 2.0

    def test_two_payloads_wait_in_separate_directories(self, tmp_path):
        other = json.dumps({"hook_event_name": "SubagentStart", "agent_id": "a1"})

        assert ordering.slot_dir(tmp_path, PAYLOAD) != ordering.slot_dir(tmp_path, other)


class TestPruning:
    def test_registering_part_one_removes_directories_older_than_an_hour(self, tmp_path):
        stale = ordering.slot_dir(tmp_path, "an old payload")
        stale.mkdir(parents=True)
        hour_ago = time.time() - 3700
        os.utime(stale, (hour_ago, hour_ago))
        fresh = ordering.slot_dir(tmp_path, PAYLOAD)

        ordering.register(fresh, 1)

        assert not stale.exists(), "a stale invocation directory survived part 1's registration"
        assert fresh.exists()


class TestTheHookWaits:
    def test_the_hook_registers_its_own_process_for_its_part(self, tmp_path):
        corpus = build_two_part_corpus(tmp_path)
        state = tmp_path / "state"

        result = subprocess.run(
            [sys.executable, str(HOOK), "--root", str(corpus), "--state", str(state),
             "--part", "1"],
            input=PAYLOAD, capture_output=True, text=True, env={"PATH": "/usr/bin:/bin"},
        )

        assert result.returncode == 0
        assert ordering.wait_for_predecessor(
            ordering.slot_dir(state, PAYLOAD), 2, deadline=0.5
        ), "part 1 left no registration for part 2 to wait on"

    def test_part_two_exits_only_after_part_one_is_gone(self, tmp_path):
        corpus = build_two_part_corpus(tmp_path)
        state = tmp_path / "state"
        predecessor = hold_open(ordering.slot_dir(state, PAYLOAD))

        part_two = subprocess.Popen(
            [sys.executable, str(HOOK), "--root", str(corpus), "--state", str(state),
             "--part", "2"],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True,
            env={"PATH": "/usr/bin:/bin"},
        )
        part_two.stdin.write(PAYLOAD)
        part_two.stdin.close()
        time.sleep(1.0)
        exited_early = part_two.poll() is not None
        predecessor.communicate(b"")
        out = part_two.stdout.read()
        part_two.wait(5.0)

        assert not exited_early, "part 2 exited while part 1's process was still running"
        context = json.loads(out)["hookSpecificOutput"]["additionalContext"]
        assert "part 2 of 2" in context
