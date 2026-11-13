#!/usr/bin/env python3
"""What one call holds and reads stays with that call: its part locks and its home directory.

Serves every session the plugin delivers rules to, and the tests that call the hooks in-process:
part k of a delivery waits for part k-1 to let go of its lock, so a call that keeps its lock past
its own end stalls every later part, and a call that reads the running process's home reads a
directory no payload named.

Run with `.venv/bin/python -m pytest features/plugins/rulesets/tests/test_call_scope.py`.
"""

import json
import pathlib
import time

import pytest
from delivery_world import DELIVER, core_rules_config, scratch_environment
from rulesets import ordering
from rulesets.cli import main
from rulesets.documents import home_relative
from rulesets.hook_entry import deliver

SESSION_START = json.dumps(
    {"session_id": "s1", "source": "startup", "model": "claude-opus-5-5"}
).encode("utf-8")


@pytest.fixture
def environ(tmp_path) -> dict[str, str]:
    core_rules_config(tmp_path, "Rule text.\n")
    return scratch_environment(tmp_path)


class TestEachDeliveryCallOwnsItsPartLocks:
    def test_a_later_part_goes_ahead_once_the_part_before_it_is_released(self, environ) -> None:
        first = deliver([str(DELIVER), "--part", "1"], SESSION_START, environ)
        first.release()

        start = time.monotonic()
        second = deliver([str(DELIVER), "--part", "2"], SESSION_START, environ)
        elapsed = time.monotonic() - start
        second.release()

        assert elapsed < ordering.ORDER_DEADLINE / 3, (
            f"part 2 took {elapsed:.2f}s after part 1 let go of its lock"
        )

    def test_a_later_part_waits_while_the_part_before_it_holds_its_lock(self, tmp_path) -> None:
        slots = tmp_path / "order" / "slot"
        first = ordering.Locks()
        ordering.hold(slots, "generation", 1, first)

        waited_out = ordering.wait_for_predecessor(slots, "generation", 2, deadline=0.2)
        first.release()
        went_ahead = ordering.wait_for_predecessor(slots, "generation", 2, deadline=1.0)

        assert (waited_out, went_ahead) == (False, True)


class TestTheHomeDirectoryComesFromTheMapping:
    def test_a_path_under_the_mappings_home_is_named_from_tilde(
        self, tmp_path, monkeypatch
    ) -> None:
        monkeypatch.setenv("HOME", str(tmp_path / "process-home"))
        mapped = tmp_path / "mapped-home"

        named = home_relative(mapped / ".claude" / "rule.md", {"HOME": str(mapped)})

        assert named == "~/.claude/rule.md"


class TestTheCommandLineReadsTheMappingItIsGiven:
    def test_a_toggle_writes_the_session_state_under_the_mappings_configuration(
        self, environ, capsys
    ) -> None:
        status = main(["toggle", "--session", "s1", "all"], environ)

        state = pathlib.Path(environ["CLAUDE_CONFIG_DIR"]) / ".tmp" / "rulesets-engine"
        assert (status, capsys.readouterr().out) == (
            0,
            "Delegates started from now on receive every rule in the pool.\n",
        )
        assert (state / "session" / "s1.yaml").is_file()
