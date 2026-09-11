"""Tests for the verify-marks hook, run from the plugin root:

    python3.14 -m pytest tests -v

Each test drives the entrypoint through stdin the way the harness does, and
builds every fixture it needs in a temporary directory: the transcripts it
scans and the state directory it writes. No test reads a real session's
transcript, a real settings file, or state a real session keeps, and run_hook
drops the two variables that could point the hook at any of them.
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = PLUGIN_ROOT / "hooks" / "verify-marks.py"


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


def read_call(path, call_id="r1"):
    block = {"type": "tool_use", "id": call_id, "name": "Read", "input": {"file_path": path}}
    return entry("assistant", [block])


def grep_call(pattern, path, call_id="g1"):
    block = {
        "type": "tool_use",
        "id": call_id,
        "name": "Grep",
        "input": {"pattern": pattern, "path": path},
    }
    return entry("assistant", [block])


def result_for(call_id, content):
    return entry("user", [{"type": "tool_result", "tool_use_id": call_id, "content": content}])


def run_hook(payload, *args, env=None):
    """Drive the entrypoint the way the harness does, on a scrubbed env.

    Both variables that could point the hook at a real session's state are
    dropped before the run, so a test reaches that state on no machine even
    when the developer's shell exports one of them. A case that needs state
    passes a temporary directory of its own.
    """
    inherited = {
        key: value
        for key, value in os.environ.items()
        if key not in ("VERIFY_MARKS_STATE_DIR", "CLAUDE_PLUGIN_DATA")
    }
    completed = subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        check=False,
        env={**inherited, **(env or {})},
    )
    return completed.returncode, completed.stdout


class VerifyMarksStopHook(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.state = str(Path(self._tmp.name) / "state")

    def transcript(self, *lines):
        path = Path(self._tmp.name) / "session.jsonl"
        path.write_text("\n".join(lines) + "\n")
        return str(path)

    def decision(self, payload):
        code, out = run_hook(payload, env={"VERIFY_MARKS_STATE_DIR": self.state})
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

    def test_a_mark_inside_a_code_span_of_its_own_blocks(self):
        result = self.decision(
            {
                "stop_hook_active": False,
                "last_assistant_message": (
                    "That count came back from the background agent at 146 test files "
                    "`[.?]` (its own caveat: regex-based, not type-aware)."
                ),
            }
        )
        self.assertIsNotNone(result, "backticks around a mark leave it a mark")
        self.assertEqual(result["decision"], "block")
        self.assertIn("146 test files", result["reason"])

    def test_a_mark_inside_a_code_span_does_not_block_when_the_line_names_it_in_words(self):
        result = self.decision(
            {
                "stop_hook_active": False,
                "last_assistant_message": (
                    "The secondhand mark, `[.?]`, is what a delegate's claim carries."
                ),
            }
        )
        self.assertNotIn(
            "decision",
            result or {},
            "a glyph beside the mark's own name documents the mark rather than claiming",
        )

    def test_a_table_pairing_every_mark_with_its_name_does_not_block(self):
        result = self.decision(
            {
                "stop_hook_active": False,
                "last_assistant_message": (
                    "| Mark | Name |\n"
                    "| --- | --- |\n"
                    "| `[?]` | the unsourced mark |\n"
                    "| `[.?]` | the secondhand mark |\n"
                ),
            }
        )
        self.assertNotIn(
            "decision",
            result or {},
            "the plugin must be able to document its own vocabulary in a reply",
        )

    def test_a_skipped_mention_reaches_the_user_in_a_notice(self):
        line = "The secondhand mark, `[.?]`, is what a delegate's claim carries."
        result = self.decision({"stop_hook_active": False, "last_assistant_message": line})
        self.assertIsNotNone(result, "an exemption a writer can take must not be silent")
        self.assertIn(line, result["systemMessage"])

    def test_a_bare_mark_still_blocks_on_a_line_documenting_that_same_mark(self):
        result = self.decision(
            {
                "stop_hook_active": False,
                "last_assistant_message": (
                    "The unsourced mark, `[?]`, says no source is on file, "
                    "and nobody else calls it [?]."
                ),
            }
        )
        self.assertIsNotNone(result, "the exemption covers the code span alone, never the line")
        self.assertEqual(result["decision"], "block")
        self.assertIn("nobody else calls it [?]", result["reason"])

    def test_a_mark_inside_a_code_span_blocks_when_the_line_names_a_different_mark(self):
        result = self.decision(
            {
                "stop_hook_active": False,
                "last_assistant_message": (
                    "Unlike the unsourced mark, this count came back from a delegate `[.?]`."
                ),
            }
        )
        self.assertIsNotNone(result, "naming one mark exempts no other mark's glyph")
        self.assertEqual(result["decision"], "block")
        self.assertIn("came back from a delegate", result["reason"])

    def test_the_reason_offers_the_referral_resolution_beside_the_verification_one(self):
        result = self.decision(
            {"stop_hook_active": False, "last_assistant_message": "The count is 12 [?]."}
        )
        reason = result["reason"]
        self.assertIn("refers to a mark", reason, "a line may discuss a mark rather than claim")
        self.assertIn("in words", reason, "the reference goes in words, never as the glyph")
        self.assertIn(
            "what you did about it", reason, "a referral names the action it already took"
        )
        self.assertIn("what you do next", reason, "or the action it is about to take")

    def test_a_mark_inside_a_longer_code_span_does_not_block(self):
        result = self.decision(
            {
                "stop_hook_active": False,
                "last_assistant_message": (
                    "The rule reads `state the premise marked [?] in the same message`, "
                    "and `MARKS = ('[?]', '[.?]', '[^?]')` names them in the hook."
                ),
            }
        )
        self.assertIsNone(result, "a span holding code or a quoted rule line stays code")

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
        code, out = run_hook(payload, "--delegate", env={"VERIFY_MARKS_STATE_DIR": self.state})
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

    def test_a_delegate_report_scans_its_own_agent_transcript_not_the_shared_session_one(self):
        # The harness gives every hook call in a session the same common
        # transcript_path (the session-level file), and adds
        # agent_transcript_path only for SubagentStop, naming that subagent's
        # own file. The session file holds the orchestrator's turns, so
        # scanning transcript_path here would hand a delegate marks the
        # orchestrator wrote.
        session_transcript = Path(self._tmp.name) / "session.jsonl"
        session_transcript.write_text(
            "\n".join(
                [
                    user_text("earlier orchestrator turn"),
                    assistant_text("A sibling agent's finding stands unverified [?]."),
                ]
            )
            + "\n"
        )
        agent_transcript = Path(self._tmp.name) / "agent-this-one.jsonl"
        agent_transcript.write_text(
            "\n".join(
                [
                    user_text("do the KV-cache task"),
                    assistant_text("The KV-cache fits comfortably, source verified."),
                ]
            )
            + "\n"
        )
        result = self.delegate_decision(
            {
                "stop_hook_active": False,
                "transcript_path": str(session_transcript),
                "agent_transcript_path": str(agent_transcript),
                "last_assistant_message": "The KV-cache fits comfortably, source verified.",
            }
        )
        self.assertIsNone(
            result,
            "a SubagentStop pass must scan the calling agent's own transcript, "
            "not the shared session transcript another agent also wrote marks into",
        )

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

    def test_the_standing_question_blocks_and_routes_to_ask_user_question(self):
        result = self.decision(
            {
                "stop_hook_active": False,
                "last_assistant_message": "Whether to ship behind a flag is unsettled [!?].",
            }
        )
        self.assertIsNotNone(result, "a [!?] line must block the stop")
        self.assertEqual(result["decision"], "block")
        self.assertIn("Whether to ship behind a flag is unsettled [!?].", result["reason"])
        self.assertIn("AskUserQuestion", result["reason"])

    def test_a_delegate_report_carrying_only_a_standing_question_does_not_block(self):
        result = self.delegate_decision(
            {
                "stop_hook_active": False,
                "last_assistant_message": "Whether to ship behind a flag is unsettled [!?].",
            }
        )
        self.assertIsNone(
            result, "a [!?] must ride up to the caller rather than stall the delegate"
        )

    def test_a_delegate_report_tells_the_caller_not_to_absorb_a_standing_question(self):
        result = self.delegate_decision(
            {
                "stop_hook_active": False,
                "last_assistant_message": (
                    "The count is 12 [?].\nWhether to ship behind a flag is unsettled [!?]."
                ),
            }
        )
        self.assertIsNotNone(result)
        reason = result["reason"]
        self.assertIn("UNANSWERED", reason)
        self.assertIn("Whether to ship behind a flag is unsettled [!?].", reason)
        self.assertIn("not absorb", reason, "the caller may relay this mark and never answer it")

    def test_a_delegate_report_lists_the_callers_mark_apart_from_the_standing_question(self):
        caller_line = "I read the request as covering staging only [^?]."
        human_line = "Whether to ship behind a flag is unsettled [!?]."
        result = self.delegate_decision(
            {
                "stop_hook_active": False,
                "last_assistant_message": f"The count is 12 [?].\n{caller_line}\n{human_line}",
            }
        )
        reason = result["reason"]
        caller_step = reason.index("[^?] exactly where it stands")
        human_step = reason.index("[!?] exactly where it stands")
        self.assertLess(
            caller_step,
            reason.index(f"- {caller_line}"),
            "the caller's mark is listed under the instruction naming it",
        )
        self.assertLess(
            human_step,
            reason.index(f"- {human_line}"),
            "the standing question is listed under its own instruction",
        )
        self.assertNotIn(
            human_line,
            reason[caller_step:human_step],
            "a caller must read the two classes apart, not as one escalation pile",
        )

    def test_a_second_pass_reports_the_surviving_marks_without_blocking(self):
        result = self.decision(
            {"stop_hook_active": True, "last_assistant_message": "Still marked [?]."}
        )
        self.assertIsNotNone(result, "a mark that survived the pass reaches the user")
        self.assertNotIn("decision", result, "a second Stop pass must not block again")
        self.assertIn("Still marked [?].", result["systemMessage"])

    def test_a_second_pass_stays_silent_when_no_mark_survives(self):
        result = self.decision(
            {"stop_hook_active": True, "last_assistant_message": "Every claim carries its source."}
        )
        self.assertIsNone(result, "a resolved reply draws no notice")

    def test_a_delegate_second_pass_hands_its_unground_claims_back_as_a_list(self):
        result = self.delegate_decision(
            {
                "stop_hook_active": True,
                "last_assistant_message": (
                    "The count is 12 [?].\nThe migration ran on every shard [.?]."
                ),
            }
        )
        self.assertIsNotNone(result, "a delegate's surviving claims must not pass in silence")
        self.assertNotIn("decision", result, "a second pass never blocks again")
        message = result["systemMessage"]
        self.assertIn("UNANSWERED", message, "the caller reads an explicit list, not prose")
        self.assertIn("The count is 12 [?].", message)
        self.assertIn("The migration ran on every shard [.?].", message)

    def test_a_main_thread_second_pass_keeps_its_plain_notice(self):
        result = self.decision(
            {"stop_hook_active": True, "last_assistant_message": "The count is 12 [?]."}
        )
        self.assertNotIn(
            "UNANSWERED",
            result["systemMessage"],
            "at top level nothing rides up, so the notice names no report opening",
        )

    def test_a_delegate_first_pass_asks_for_an_unanswered_opening_on_what_it_cannot_ground(self):
        result = self.delegate_decision(
            {"stop_hook_active": False, "last_assistant_message": "The count is 12 [?]."}
        )
        reason = result["reason"]
        self.assertIn("UNANSWERED", reason)
        self.assertIn(
            "re-delegates",
            reason,
            "the delegate is told why the list matters: the caller acts on it",
        )

    def test_a_main_thread_first_pass_asks_for_no_unanswered_opening_on_evidence_marks(self):
        result = self.decision(
            {"stop_hook_active": False, "last_assistant_message": "The count is 12 [?]."}
        )
        self.assertNotIn(
            "UNANSWERED",
            result["reason"],
            "at top level the reader is the user, who wants the reply and not a debt list",
        )

    def test_a_delegate_second_pass_stays_silent_on_a_caret_mark(self):
        result = self.delegate_decision(
            {
                "stop_hook_active": True,
                "last_assistant_message": "I read the request as covering staging only [^?].",
            }
        )
        self.assertIsNone(result, "a [^?] rides up to the caller rather than drawing a notice")


class VerifyMarksCitationIntegrity(unittest.TestCase):
    """A citation is the positive signal, so a fabricated one is worth a notice."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.state = str(Path(self._tmp.name) / "state")

    def transcript(self, *lines):
        path = Path(self._tmp.name) / "session.jsonl"
        path.write_text("\n".join(lines) + "\n")
        return str(path)

    def decision(self, reply, *lines):
        payload = {
            "stop_hook_active": False,
            "transcript_path": self.transcript(user_text("check it"), *lines),
            "last_assistant_message": reply,
        }
        code, out = run_hook(payload, env={"VERIFY_MARKS_STATE_DIR": self.state})
        self.assertEqual(code, 0)
        return json.loads(out) if out.strip() else None

    def test_a_citation_naming_a_file_nothing_opened_draws_a_notice(self):
        result = self.decision(
            "The guard lives at beta.py:42.",
            read_call("/repo/alpha.py"),
            result_for("r1", "the contents of alpha"),
        )
        self.assertIsNotNone(result, "a citation to an unopened file must reach the reader")
        self.assertIn("beta.py:42", result["systemMessage"])

    def test_a_citation_naming_a_file_a_read_opened_draws_no_notice(self):
        result = self.decision(
            "The guard lives at alpha.py:42.",
            read_call("/repo/alpha.py"),
            result_for("r1", "the contents of alpha"),
        )
        self.assertIsNone(result, "a relative citation matches the absolute path Read was given")

    def test_a_citation_naming_a_path_a_grep_returned_draws_no_notice(self):
        result = self.decision(
            "The guard lives at gamma.py:7.",
            grep_call("guard", "/repo"),
            result_for("g1", "/repo/gamma.py:7:    if guard:"),
        )
        self.assertIsNone(
            result,
            "a Grep over a directory surfaces the files in its results, "
            "and citing one of those is citing a file the session opened",
        )

    def test_a_citation_inside_a_fenced_block_draws_no_notice(self):
        result = self.decision(
            "For example:\n```\nsee beta.py:42\n```\nThat is the form.",
            read_call("/repo/alpha.py"),
            result_for("r1", "the contents of alpha"),
        )
        self.assertIsNone(result, "a citation inside an example block claims nothing")

    def test_a_citation_to_an_unopened_file_never_blocks(self):
        result = self.decision(
            "The guard lives at beta.py:42.",
            read_call("/repo/alpha.py"),
            result_for("r1", "the contents of alpha"),
        )
        self.assertNotIn("decision", result, "the citation check reports and never stops the turn")

    def test_a_blocking_pass_reports_no_citation(self):
        result = self.decision(
            "The count is 12 [?]. The guard lives at beta.py:42.",
            read_call("/repo/alpha.py"),
            result_for("r1", "the contents of alpha"),
        )
        self.assertEqual(result["decision"], "block")
        self.assertNotIn(
            "beta.py:42",
            result.get("systemMessage", ""),
            "this reply is about to be replaced, so a notice about it is noise",
        )

    def test_a_tool_result_from_a_write_leaves_a_citation_unopened(self):
        result = self.decision(
            "The guard lives at beta.py:42.",
            entry(
                "assistant",
                [
                    {
                        "type": "tool_use",
                        "id": "w1",
                        "name": "Write",
                        "input": {"file_path": "/repo/beta.py"},
                    }
                ],
            ),
            result_for("w1", "wrote /repo/beta.py"),
        )
        self.assertIsNotNone(
            result, "only Read, Grep and Glob put a file in front of the agent to cite"
        )
        self.assertIn("beta.py:42", result["systemMessage"])


class VerifyMarksBatchHook(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.state = str(Path(self._tmp.name) / "state")

    def transcript(self, *lines):
        path = Path(self._tmp.name) / "session.jsonl"
        path.write_text("\n".join(lines) + "\n")
        return str(path)

    def agent_transcript(self, agent_id, *lines, workflow=None):
        """A subagent's own transcript, where the harness writes one.

        The path is `<session transcript stem>/subagents/agent-<id>.jsonl`,
        with a workflow agent's file one level deeper under `workflows/<wf>/`.
        """
        directory = Path(self._tmp.name) / "session" / "subagents"
        if workflow:
            directory = directory / "workflows" / workflow
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / f"agent-{agent_id}.jsonl"
        path.write_text("\n".join(lines) + "\n")
        return str(path)

    def batch(self, transcript, session_id="session-one", **extra):
        payload = {
            "hook_event_name": "PostToolBatch",
            "session_id": session_id,
            "transcript_path": transcript,
            "tool_calls": [],
        }
        payload.update(extra)
        code, out = run_hook(
            payload,
            "--batch",
            env={"VERIFY_MARKS_STATE_DIR": self.state},
        )
        self.assertEqual(code, 0)
        return json.loads(out) if out.strip() else None

    def context_of(self, result):
        self.assertIsNotNone(result)
        self.assertNotIn("decision", result, "a batch pass never blocks the loop")
        specific = result["hookSpecificOutput"]
        self.assertEqual(specific["hookEventName"], "PostToolBatch")
        return specific["additionalContext"]

    def test_batch_reports_a_marked_line_written_earlier_in_the_open_turn(self):
        transcript = self.transcript(
            user_text("do the thing"),
            assistant_text("The endpoint has no other callers [?]."),
            assistant_tool_use(),
            tool_result(),
        )
        context = self.context_of(self.batch(transcript))
        self.assertIn("The endpoint has no other callers [?].", context)

    def test_batch_stays_silent_when_the_open_turn_carries_no_mark(self):
        transcript = self.transcript(
            user_text("do the thing"),
            assistant_text("Every claim here carries its source."),
            assistant_tool_use(),
            tool_result(),
        )
        self.assertIsNone(self.batch(transcript), "an unmarked turn draws no context")

    def test_batch_reports_a_line_once_per_session(self):
        transcript = self.transcript(
            user_text("do the thing"),
            assistant_text("The endpoint has no other callers [?]."),
            assistant_tool_use(),
            tool_result(),
        )
        self.assertIsNotNone(self.batch(transcript))
        self.assertIsNone(
            self.batch(transcript),
            "a line already handed back must not repeat on every later batch",
        )

    def test_batch_reports_a_mark_that_appeared_since_the_last_batch(self):
        first = self.transcript(
            user_text("do the thing"),
            assistant_text("The endpoint has no other callers [?]."),
        )
        self.batch(first)
        second = self.transcript(
            user_text("do the thing"),
            assistant_text("The endpoint has no other callers [?]."),
            assistant_tool_use(),
            tool_result(),
            assistant_text("The migration ran on every shard [.?]."),
        )
        context = self.context_of(self.batch(second))
        self.assertIn("The migration ran on every shard [.?].", context)
        self.assertNotIn("no other callers", context, "the reported line stays reported")

    def test_batch_reports_the_same_line_again_under_a_different_session(self):
        transcript = self.transcript(
            user_text("do the thing"),
            assistant_text("The endpoint has no other callers [?]."),
        )
        self.batch(transcript, session_id="session-one")
        context = self.context_of(self.batch(transcript, session_id="session-two"))
        self.assertIn("The endpoint has no other callers [?].", context)

    def test_batch_routes_a_caret_mark_to_ask_user_question(self):
        transcript = self.transcript(
            user_text("do the thing"),
            assistant_text("I read the request as covering staging only [^?]."),
        )
        context = self.context_of(self.batch(transcript))
        self.assertIn("I read the request as covering staging only [^?].", context)
        self.assertIn("AskUserQuestion", context)

    def test_batch_reports_a_delegates_own_mark_from_its_own_transcript(self):
        # PostToolBatch carries session_id, transcript_path and, from within
        # a subagent, agent_id; agent_transcript_path reaches SubagentStop
        # alone. The harness writes a subagent's turns to a file of their own
        # under the session transcript's stem, so the delegate's own marks
        # are the ones this pass must reach for, and the orchestrator's are
        # the ones it must leave alone.
        transcript = self.transcript(
            user_text("earlier orchestrator turn"),
            assistant_text("The orchestrator's own claim stands unverified [?]."),
        )
        self.agent_transcript(
            "two",
            user_text("do the KV-cache task"),
            assistant_text("The KV-cache holds every shard [?]."),
        )
        context = self.context_of(self.batch(transcript, agent_id="two"))
        self.assertIn("The KV-cache holds every shard [?].", context)
        self.assertNotIn(
            "orchestrator's own claim",
            context,
            "a delegate must not be handed a mark the orchestrator wrote",
        )

    def test_batch_reports_a_workflow_delegates_mark_from_its_nested_transcript(self):
        transcript = self.transcript(user_text("do the thing"))
        self.agent_transcript(
            "three",
            user_text("do the shard task"),
            assistant_text("The shard count is 12 [?]."),
            workflow="wf_9f8f2559",
        )
        context = self.context_of(self.batch(transcript, agent_id="three"))
        self.assertIn("The shard count is 12 [?].", context)

    def test_batch_stays_silent_when_a_delegate_has_no_transcript_of_its_own(self):
        transcript = self.transcript(
            user_text("do the thing"),
            assistant_text("The orchestrator's own claim stands unverified [?]."),
        )
        self.assertIsNone(
            self.batch(transcript, agent_id="absent"),
            "with no transcript of its own a delegate draws nothing, "
            "rather than falling back to the shared session file",
        )

    def test_batch_keeps_a_delegates_ledger_apart_from_the_main_threads(self):
        line = "The endpoint has no other callers [?]."
        transcript = self.transcript(user_text("do the thing"), assistant_text(line))
        self.agent_transcript("two", user_text("do the sub task"), assistant_text(line))
        self.assertIsNotNone(self.batch(transcript, agent_id="two"))
        context = self.context_of(self.batch(transcript))
        self.assertIn(
            line,
            context,
            "a delegate's ledger must not suppress the same sentence for the main thread",
        )

    def test_a_subagent_batch_leaves_the_main_threads_report_standing(self):
        transcript = self.transcript(
            user_text("do the thing"),
            assistant_text("The endpoint has no other callers [?]."),
        )
        self.batch(transcript, agent_id="agent-two")
        context = self.context_of(self.batch(transcript))
        self.assertIn(
            "The endpoint has no other callers [?].",
            context,
            "a subagent's batch must not record a line the main thread never heard about",
        )

    def test_batch_stays_silent_without_a_readable_transcript(self):
        code, out = run_hook(
            {"hook_event_name": "PostToolBatch", "session_id": "session-one"},
            "--batch",
            env={"VERIFY_MARKS_STATE_DIR": self.state},
        )
        self.assertEqual(code, 0)
        self.assertEqual(out.strip(), "", "no transcript means nothing to scan")


if __name__ == "__main__":
    unittest.main()
