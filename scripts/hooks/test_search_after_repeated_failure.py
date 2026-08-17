"""Tests for search-after-repeated-failure.py, run from this directory:

    python3 -m pytest test_search_after_repeated_failure.py -v

Each test drives the script through stdin the way the hook does, with
CLAUDE_REPEAT_FAILURE_DIR pointing at a temporary directory so no test
touches the real session state.
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).with_name("search-after-repeated-failure.py")


class RepeatedFailureHook(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.env = dict(os.environ, CLAUDE_REPEAT_FAILURE_DIR=self._tmp.name)

    def run_hook(self, payload):
        completed = subprocess.run(
            [sys.executable, str(SCRIPT)],
            input=json.dumps(payload),
            capture_output=True,
            text=True,
            env=self.env,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        out = completed.stdout.strip()
        return json.loads(out) if out else None

    def failure(self, command="bun test", error="Exit code 1\nCannot find module", **extra):
        payload = {
            "session_id": "s1",
            "hook_event_name": "PostToolUseFailure",
            "tool_name": "Bash",
            "tool_input": {"command": command},
            "error": error,
        }
        payload.update(extra)
        return self.run_hook(payload)

    def success(self, session_id="s1"):
        return self.run_hook(
            {
                "session_id": session_id,
                "hook_event_name": "PostToolUse",
                "tool_name": "Bash",
                "tool_input": {"command": "ls"},
            }
        )

    def context(self, result):
        self.assertIsNotNone(result)
        return result["hookSpecificOutput"]["additionalContext"]

    def test_the_first_failure_demands_the_lookup(self):
        context = self.context(self.failure())
        self.assertIn("Read before attempting again", context)
        self.assertIn("read the installed artifact and search the live", context)

    def test_the_first_failure_names_no_streak(self):
        context = self.context(self.failure())
        self.assertIn("A tool call failed", context)
        self.assertNotIn("in a row", context)

    def test_a_second_consecutive_failure_reports_the_streak_length(self):
        self.failure()
        context = self.context(self.failure())
        self.assertIn("2 tool calls have failed in a row", context)
        self.assertIn("Stop attempting", context)

    def test_a_success_between_two_failures_clears_the_count(self):
        self.failure()
        self.success()
        context = self.context(self.failure())
        self.assertIn("A tool call failed", context)
        self.assertNotIn("in a row", context)

    def test_the_reminder_lists_the_failures_it_counted(self):
        self.failure(command="bun test alpha", error="Exit code 1\nno such flag")
        context = self.context(self.failure(command="bunx vitest alpha", error="Exit code 2\nboom"))
        self.assertIn("bun test alpha", context)
        self.assertIn("bunx vitest alpha", context)

    def test_a_streak_carrying_one_error_asks_for_that_text_verbatim(self):
        self.failure(error="Exit code 1\nunknown option --isolate")
        context = self.context(self.failure(error="Exit code 1\nunknown option --isolate"))
        self.assertIn("verbatim", context)

    def test_a_streak_carrying_different_errors_skips_the_verbatim_step(self):
        self.failure(error="Exit code 1\nfirst thing")
        context = self.context(self.failure(error="Exit code 2\nsecond thing"))
        self.assertNotIn("verbatim", context)

    def test_a_lone_failure_skips_the_verbatim_step(self):
        context = self.context(self.failure(error="Exit code 1\nunknown option --isolate"))
        self.assertNotIn("verbatim", context)

    def test_a_bare_exit_code_carries_the_line_under_it(self):
        context = self.context(self.failure(error="Exit code 1\nunknown option --isolate"))
        self.assertIn("unknown option --isolate", context)

    def test_an_error_naming_itself_on_the_first_line_stops_there(self):
        context = self.context(
            self.failure(error="String to replace not found in file.\nAt line 40 of a diff")
        )
        self.assertIn("String to replace not found in file.", context)
        self.assertNotIn("At line 40", context)

    def test_an_error_with_no_text_still_produces_a_reminder(self):
        context = self.context(self.failure(error=""))
        self.assertIn("no error text", context)

    def test_every_reminder_excuses_a_predicted_red_test(self):
        context = self.context(self.failure(command="bun test", error="Exit code 1\n1 failed"))
        self.assertIn("red step you predicted", context)

    def test_an_interrupt_never_counts_toward_the_streak(self):
        self.assertIsNone(self.failure(is_interrupt=True), "an abort reports no wrong model")
        context = self.context(self.failure())
        self.assertNotIn("in a row", context, "the aborted call left no count behind")

    def test_two_sessions_keep_separate_counts(self):
        self.failure()
        other = self.run_hook(
            {
                "session_id": "s2",
                "hook_event_name": "PostToolUseFailure",
                "tool_name": "Bash",
                "tool_input": {"command": "cargo build"},
                "error": "Exit code 101",
            }
        )
        context = other["hookSpecificOutput"]["additionalContext"]
        self.assertNotIn("in a row", context, "another session starts its own streak")

    def test_a_failing_edit_names_the_file_it_targeted(self):
        self.run_hook(
            {
                "session_id": "s1",
                "hook_event_name": "PostToolUseFailure",
                "tool_name": "Edit",
                "tool_input": {"file_path": "/repo/src/main.ts"},
                "error": "String to replace not found",
            }
        )
        context = self.context(
            self.run_hook(
                {
                    "session_id": "s1",
                    "hook_event_name": "PostToolUseFailure",
                    "tool_name": "Edit",
                    "tool_input": {"file_path": "/repo/src/main.ts"},
                    "error": "String to replace not found",
                }
            )
        )
        self.assertIn("/repo/src/main.ts", context)


if __name__ == "__main__":
    unittest.main()
