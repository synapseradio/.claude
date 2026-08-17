"""Tests for verify-marks.py, run from this directory:

    python3 -m pytest test_verify_marks.py -v

Each test drives the script through stdin the way the Stop hook does, with a
JSONL transcript written to a temporary file where the case needs one.
"""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).with_name("verify-marks.py")


def entry(kind, content):
    return json.dumps({"type": kind, "message": {"role": kind, "content": content}})


def user_text(text):
    return entry("user", text)


def tool_result():
    return entry("user", [{"type": "tool_result", "tool_use_id": "t1", "content": "ok"}])


def assistant_text(text):
    return entry("assistant", [{"type": "text", "text": text}])


def assistant_tool_use():
    return entry("assistant", [{"type": "tool_use", "id": "t1", "name": "Read", "input": {}}])


def run_hook(payload, *args):
    completed = subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        check=False,
    )
    return completed.returncode, completed.stdout


class VerifyMarksStopHook(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)

    def transcript(self, *lines):
        path = Path(self._tmp.name) / "session.jsonl"
        path.write_text("\n".join(lines) + "\n")
        return str(path)

    def decision(self, payload):
        code, out = run_hook(payload)
        self.assertEqual(code, 0)
        return json.loads(out) if out.strip() else None

    def test_stop_blocks_on_a_marked_line_since_the_last_real_user_message(self):
        transcript = self.transcript(
            user_text("earlier question"),
            assistant_text("Old reply, no mark."),
            user_text("do the thing"),
            assistant_text("The endpoint has no other callers [?]."),
            assistant_tool_use(),
            tool_result(),
        )
        result = self.decision(
            {
                "stop_hook_active": False,
                "transcript_path": transcript,
                "last_assistant_message": "Done.",
            }
        )
        self.assertIsNotNone(result, "a [?] line inside the turn must block the stop")
        self.assertEqual(result["decision"], "block")
        self.assertIn("The endpoint has no other callers [?].", result["reason"])
        self.assertNotIn("Old reply", result["reason"])

    def test_a_mark_inside_last_assistant_message_alone_still_blocks(self):
        result = self.decision(
            {
                "stop_hook_active": False,
                "last_assistant_message": "The delegate reports it migrated [.?].",
            }
        )
        self.assertIsNotNone(
            result, "a mark in last_assistant_message must block without a transcript"
        )
        self.assertEqual(result["decision"], "block")
        self.assertIn("The delegate reports it migrated [.?].", result["reason"])

    def test_caret_mark_blocks_and_hands_back_the_ask_user_question_resolution(self):
        result = self.decision(
            {
                "stop_hook_active": False,
                "last_assistant_message": "I read the request as covering staging only [^?].",
            }
        )
        self.assertIsNotNone(result, "a [^?] line must block the stop")
        self.assertEqual(result["decision"], "block")
        reason = result["reason"]
        self.assertIn("I read the request as covering staging only [^?].", reason)
        self.assertIn("AskUserQuestion", reason)
        self.assertIn("[^?]", reason.split("\n", 1)[0], "the opening line names the mark it found")

    def test_reason_groups_lines_under_the_mark_each_one_carries(self):
        result = self.decision(
            {
                "stop_hook_active": False,
                "last_assistant_message": (
                    "No other team depends on this endpoint [?].\n"
                    "I read the request as covering staging only [^?]."
                ),
            }
        )
        reason = result["reason"]
        source_heading = reason.index("Marked [?]")
        question_heading = reason.index("Marked [^?]")
        source_line = reason.index("No other team depends on this endpoint [?].")
        question_line = reason.index("I read the request as covering staging only [^?].")
        self.assertLess(source_heading, source_line)
        self.assertLess(source_line, question_heading)
        self.assertLess(question_heading, question_line)

    def test_a_mark_inside_a_fenced_code_block_does_not_block(self):
        transcript = self.transcript(
            user_text("show me the rule"),
            assistant_text(
                "Here it is:\n```\nmark it `[?]` when no source exists\n```\nThat is all."
            ),
        )
        result = self.decision(
            {
                "stop_hook_active": False,
                "transcript_path": transcript,
                "last_assistant_message": "That is all.",
            }
        )
        self.assertIsNone(result, "a mark quoted inside a fence must not block")

    def test_an_unclosed_fence_hides_no_later_mark(self):
        result = self.decision(
            {
                "stop_hook_active": False,
                "last_assistant_message": (
                    "Example:\n```python\nfoo()\n\nNobody else calls it [?]."
                ),
            }
        )
        self.assertIsNotNone(result, "a fence that never closes must exclude nothing")
        self.assertIn("Nobody else calls it [?].", result["reason"])

    def test_a_shorter_inner_delimiter_does_not_close_the_outer_fence(self):
        result = self.decision(
            {
                "stop_hook_active": False,
                "last_assistant_message": (
                    "Doc:\n````markdown\n```sh\nrun\n````\nThe rename is safe [?]."
                ),
            }
        )
        self.assertIsNotNone(result, "a ``` inside a ```` fence must not end the fence")
        self.assertIn("The rename is safe [?].", result["reason"])

    def test_a_fence_spanning_two_text_blocks_still_ends_at_its_closing_delimiter(self):
        transcript = self.transcript(
            user_text("go"),
            entry(
                "assistant",
                [
                    {"type": "text", "text": "Start:\n```python"},
                    {"type": "text", "text": "foo()\n```\nThe count is 12 [?]."},
                ],
            ),
        )
        result = self.decision(
            {"stop_hook_active": False, "transcript_path": transcript, "last_assistant_message": ""}
        )
        self.assertIsNotNone(result, "fence state must carry across text blocks of one turn")
        self.assertIn("The count is 12 [?].", result["reason"])

    def test_a_mark_mentioned_inside_an_inline_code_span_does_not_block(self):
        result = self.decision(
            {
                "stop_hook_active": False,
                "last_assistant_message": (
                    "MARKS gains `[^?]`, and `[?]` or `[.?]` keep the verify step. "
                    "The rule at `core-rules:87` lists `[?]`, `[.?]`, `[^?]`."
                ),
            }
        )
        self.assertIsNone(result, "a mark quoted inside backticks is a mention, and must not block")

    def test_a_mark_outside_a_code_span_on_a_line_that_also_mentions_one_blocks(self):
        result = self.decision(
            {
                "stop_hook_active": False,
                "last_assistant_message": "The `[?]` rule applies here: nobody else calls it [?].",
            }
        )
        self.assertIsNotNone(result, "a real mark beside a quoted one still blocks")
        self.assertIn("nobody else calls it [?].", result["reason"])

    def delegate_decision(self, payload):
        code, out = run_hook(payload, "--delegate")
        self.assertEqual(code, 0)
        return json.loads(out) if out.strip() else None

    def test_a_delegate_report_carrying_only_a_caret_mark_does_not_block(self):
        result = self.delegate_decision(
            {
                "stop_hook_active": False,
                "last_assistant_message": "I read the request as covering staging only [^?].",
            }
        )
        self.assertIsNone(
            result, "a [^?] must ride up to the caller rather than stall the delegate"
        )

    def test_a_delegate_report_blocks_on_a_source_mark(self):
        result = self.delegate_decision(
            {"stop_hook_active": False, "last_assistant_message": "The count is 12 [?]."}
        )
        self.assertIsNotNone(result, "a delegate resolves the marks it can settle itself")
        self.assertIn("The count is 12 [?].", result["reason"])

    def test_a_delegate_report_mixing_marks_blocks_and_routes_the_caret_upward(self):
        result = self.delegate_decision(
            {
                "stop_hook_active": False,
                "last_assistant_message": (
                    "The count is 12 [?].\nI read the request as covering staging only [^?]."
                ),
            }
        )
        self.assertIsNotNone(result)
        reason = result["reason"]
        self.assertIn("UNANSWERED", reason)
        self.assertIn("I read the request as covering staging only [^?].", reason)
        self.assertNotIn("call AskUserQuestion with the question", reason)

    def test_the_main_agent_still_routes_a_caret_mark_to_ask_user_question(self):
        result = self.decision(
            {
                "stop_hook_active": False,
                "last_assistant_message": "I read the request as covering staging only [^?].",
            }
        )
        self.assertIsNotNone(result, "without --delegate the caret mark keeps its blocking pass")
        self.assertIn("AskUserQuestion", result["reason"])
        self.assertNotIn("UNANSWERED", result["reason"])

    def test_stop_hook_active_exits_silently(self):
        result = self.decision(
            {"stop_hook_active": True, "last_assistant_message": "Still marked [?]."}
        )
        self.assertIsNone(result, "a second Stop pass in the same cycle must not block again")


if __name__ == "__main__":
    unittest.main()
