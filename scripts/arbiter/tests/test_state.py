"""Regression tests for `lib.state` error handling.

The error policy in `state.py` distinguishes the file-already-gone
race from real failures (permission denied, disk full). The race is
silent; everything else logs to `arbiter.log` under `event=state`
before the function returns its safe default.

These tests pin that contract: if a future refactor re-broadens
`except OSError` to silently swallow unexpected errors, the silent
permission-disable failure mode would surface immediately when CI
runs this file.

Run from `scripts/arbiter/`:

    python3 -m unittest tests.test_state
"""

import json
import pathlib

# Make the arbiter package importable when running this file directly
# (`python3 -m unittest tests.test_state` from scripts/arbiter/).
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from lib import state


class StateLoggingTest(unittest.TestCase):
    """Each test runs in a temp directory with `state.STATE_DIR` and
    `state.LOG_PATH` patched onto it. The log is read back as text so
    assertions match on the literal `event=state` line shape."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        root = pathlib.Path(self._tmp.name)
        self._state_dir = root / "arbiter-flows"
        self._log_path = root / "arbiter.log"
        self._patches = [
            mock.patch.object(state, "STATE_DIR", self._state_dir),
            mock.patch.object(state, "LOG_PATH", self._log_path),
        ]
        for p in self._patches:
            p.start()
            self.addCleanup(p.stop)

    def _log_text(self) -> str:
        if not self._log_path.exists():
            return ""
        return self._log_path.read_text(encoding="utf-8")

    def _seed_flow(self, transcript: str, tool: str, payload: dict | None = None) -> pathlib.Path:
        self._state_dir.mkdir(parents=True, exist_ok=True)
        path = state._flow_path(transcript, tool)
        path.write_text(
            json.dumps(payload or {"first_blocked_at": "2099-01-01T00:00:00Z", "tool": tool})
        )
        return path

    # --- Happy paths emit nothing under event=state ---------------------

    def test_record_first_block_happy_path_no_log(self) -> None:
        ok = state.record_first_block("/tmp/some-transcript.jsonl", "ExitPlanMode")
        self.assertTrue(ok)
        self.assertNotIn("event=state", self._log_text())

    def test_has_first_block_happy_path_no_log(self) -> None:
        self._seed_flow("/tmp/some-transcript.jsonl", "ExitPlanMode")
        self.assertTrue(state.has_first_block("/tmp/some-transcript.jsonl", "ExitPlanMode"))
        self.assertNotIn("event=state", self._log_text())

    # --- File-already-gone race is silent --------------------------------

    def test_unlink_filenotfound_is_silent(self) -> None:
        path = self._state_dir / "does-not-exist.json"
        self._state_dir.mkdir(parents=True, exist_ok=True)
        state._safe_unlink(path, "test-race")
        self.assertNotIn("event=state", self._log_text())

    # --- Real OSError on cleanup unlink lands a log line -----------------

    def test_unlink_permission_error_logs(self) -> None:
        path = self._state_dir / "x.json"
        self._state_dir.mkdir(parents=True, exist_ok=True)
        path.write_text("{}")
        with mock.patch.object(pathlib.Path, "unlink", side_effect=PermissionError("denied")):
            state._safe_unlink(path, "test-perm")
        log = self._log_text()
        self.assertIn("event=state", log)
        self.assertIn("ERROR:test-perm-unlink:PermissionError", log)

    # --- record_first_block: every fail-closed branch logs ---------------

    def test_record_mkdir_error_logs_and_returns_false(self) -> None:
        # Patch pathlib.Path.mkdir selectively: STATE_DIR raises (the
        # case we're exercising), but LOG_PATH.parent.mkdir still works
        # so the logger itself can land its line.
        real_mkdir = pathlib.Path.mkdir

        def selective(self_, *args, **kwargs):
            if self_ == state.STATE_DIR:
                raise PermissionError("denied")
            return real_mkdir(self_, *args, **kwargs)

        with mock.patch.object(pathlib.Path, "mkdir", autospec=True, side_effect=selective):
            ok = state.record_first_block("/tmp/x.jsonl", "ExitPlanMode")
        self.assertFalse(ok)
        self.assertIn("ERROR:record-mkdir:PermissionError", self._log_text())

    def test_record_open_error_logs_and_returns_false(self) -> None:
        with mock.patch("os.open", side_effect=PermissionError("denied")):
            ok = state.record_first_block("/tmp/y.jsonl", "ExitPlanMode")
        self.assertFalse(ok)
        self.assertIn("ERROR:record-open:PermissionError", self._log_text())

    def test_record_write_error_logs_rolls_back_and_returns_false(self) -> None:
        with mock.patch("os.fdopen", side_effect=OSError("disk full")):
            ok = state.record_first_block("/tmp/z.jsonl", "ExitPlanMode")
        self.assertFalse(ok)
        log = self._log_text()
        self.assertIn("ERROR:record-write:OSError", log)
        self.assertFalse(state._flow_path("/tmp/z.jsonl", "ExitPlanMode").exists())

    def test_record_filexists_race_is_silent(self) -> None:
        # First call wins, second loses.
        ok1 = state.record_first_block("/tmp/a.jsonl", "ExitPlanMode")
        self.assertTrue(ok1)
        prior_log = self._log_text()
        ok2 = state.record_first_block("/tmp/a.jsonl", "ExitPlanMode")
        self.assertFalse(ok2)
        self.assertEqual(self._log_text(), prior_log)

    # --- has_first_block: corrupt JSON is logged, returns False ----------

    def test_has_first_block_corrupt_file_logs(self) -> None:
        self._state_dir.mkdir(parents=True, exist_ok=True)
        path = state._flow_path("/tmp/c.jsonl", "ExitPlanMode")
        path.write_text("not json{{{")
        ok = state.has_first_block("/tmp/c.jsonl", "ExitPlanMode")
        self.assertFalse(ok)
        log = self._log_text()
        # prune_expired runs first, hits the corrupt file, logs and unlinks.
        # has_first_block then sees the file gone and returns False.
        self.assertIn("ERROR:prune-read:JSONDecodeError", log)

    # --- prune_expired: iterdir failure logs once and bails --------------

    def test_prune_iterdir_error_logs(self) -> None:
        self._state_dir.mkdir(parents=True, exist_ok=True)
        with mock.patch.object(pathlib.Path, "iterdir", side_effect=PermissionError("denied")):
            state.prune_expired()
        self.assertIn("ERROR:prune-iterdir:PermissionError", self._log_text())


if __name__ == "__main__":
    unittest.main()
