"""Tests for the verify-marks hook, run from the plugin root.

    python3 -m unittest discover -s tests -v

Each test drives the entrypoint through stdin the way the harness does, and
builds every fixture it needs in a temporary directory: the transcripts it
scans and the state directory it writes. No test reads a real session's
transcript, a real settings file, or state a real session keeps, and
isolated_environment drops the variables that could point the hook at any of them.
"""

import tempfile
import unittest
from pathlib import Path

from support import (
    assistant_text,
    entry,
    hook_output,
    isolated_environment,
    required,
    run_hook,
    user_text,
)

# The group headings, imported so a test asserting what rides up anchors on
# the heading itself rather than on a copy of its wording. conftest.py puts
# the plugin root on the import path.
from epistemic_marks.messages import RELAY_HEADING, STANDING_HEADING


def tool_result() -> str:
    return entry("user", [{"type": "tool_result", "tool_use_id": "t1", "content": "ok"}])


def assistant_tool_use() -> str:
    return entry("assistant", [{"type": "tool_use", "id": "t1", "name": "Read", "input": {}}])


class VerifyMarksStopHook(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        root = Path(self._tmp.name)
        self.env = isolated_environment(root / "home", state_dir=root / "state")

    def transcript(self, *lines) -> str:
        path = Path(self._tmp.name) / "session.jsonl"
        path.write_text("\n".join(lines) + "\n")
        return str(path)

    def decision(self, payload) -> dict | None:
        code, out, err = run_hook(payload, env=self.env)
        assert code == 0, err
        return hook_output(out)

    def test_stop_blocks_on_a_marked_line_since_the_last_real_user_message(self) -> None:
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
        assert result is not None, "a [?] line inside the turn must block the stop"
        assert result["decision"] == "block"
        assert "The endpoint has no other callers [?]." in result["reason"]
        assert "Old reply" not in result["reason"]

    def test_a_mark_inside_last_assistant_message_alone_still_blocks(self) -> None:
        result = self.decision(
            {
                "stop_hook_active": False,
                "last_assistant_message": "The delegate reports it migrated [.?].",
            }
        )
        assert result is not None, (
            "a mark in last_assistant_message must block without a transcript"
        )
        assert result["decision"] == "block"
        assert "The delegate reports it migrated [.?]." in result["reason"]

    def test_caret_mark_blocks_and_hands_back_the_callers_resolution(self) -> None:
        result = self.decision(
            {
                "stop_hook_active": False,
                "last_assistant_message": "I read the request as covering staging only [^?].",
            }
        )
        assert result is not None, "a [^?] line must block the stop"
        assert result["decision"] == "block"
        reason = result["reason"]
        assert "I read the request as covering staging only [^?]." in reason
        assert "to your caller" in reason, "the caller's mark asks its question one level up"
        assert "AskUserQuestion" not in reason, (
            "the reader runs on a machine whose toolset this plugin cannot know"
        )

    def test_the_reason_heads_each_group_with_the_glyph_its_lines_carry(self) -> None:
        result = required(
            self.decision(
                {
                    "stop_hook_active": False,
                    "last_assistant_message": "I read the request as covering staging only [^?].",
                }
            )
        )
        assert "\n[^?]\n" in result["reason"], (
            "a glyph reaches the output as the heading over the lines carrying it"
        )

    def test_reason_groups_lines_under_the_mark_each_one_carries(self) -> None:
        result = required(
            self.decision(
                {
                    "stop_hook_active": False,
                    "last_assistant_message": (
                        "No other team depends on this endpoint [?].\n"
                        "I read the request as covering staging only [^?]."
                    ),
                }
            )
        )
        reason = result["reason"]
        source_heading = reason.index("\n[?]\n")
        question_heading = reason.index("\n[^?]\n")
        source_line = reason.index("No other team depends on this endpoint [?].")
        question_line = reason.index("I read the request as covering staging only [^?].")
        assert source_heading < source_line
        assert source_line < question_heading
        assert question_heading < question_line

    def test_a_mark_inside_a_fenced_code_block_does_not_block(self) -> None:
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
        assert result is None, "a mark quoted inside a fence must not block"

    def test_an_unclosed_fence_hides_no_later_mark(self) -> None:
        result = self.decision(
            {
                "stop_hook_active": False,
                "last_assistant_message": (
                    "Example:\n```python\nfoo()\n\nNobody else calls it [?]."
                ),
            }
        )
        assert result is not None, "a fence that never closes must exclude nothing"
        assert "Nobody else calls it [?]." in result["reason"]

    def test_a_shorter_inner_delimiter_does_not_close_the_outer_fence(self) -> None:
        result = self.decision(
            {
                "stop_hook_active": False,
                "last_assistant_message": (
                    "Doc:\n````markdown\n```sh\nrun\n````\nThe rename is safe [?]."
                ),
            }
        )
        assert result is not None, "a ``` inside a ```` fence must not end the fence"
        assert "The rename is safe [?]." in result["reason"]

    def test_a_fence_spanning_two_text_blocks_still_ends_at_its_closing_delimiter(self) -> None:
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
        assert result is not None, "fence state must carry across text blocks of one turn"
        assert "The count is 12 [?]." in result["reason"]

    def test_a_mark_inside_a_code_span_of_its_own_blocks(self) -> None:
        result = self.decision(
            {
                "stop_hook_active": False,
                "last_assistant_message": (
                    "That count came back from the background agent at 146 test files "
                    "`[.?]` (its own caveat: regex-based, not type-aware)."
                ),
            }
        )
        assert result is not None, "backticks around a mark leave it a mark"
        assert result["decision"] == "block"
        assert "146 test files" in result["reason"]

    def test_a_mark_inside_a_code_span_does_not_block_when_the_line_names_it_in_words(self) -> None:
        result = self.decision(
            {
                "stop_hook_active": False,
                "last_assistant_message": (
                    "The secondhand mark, `[.?]`, is what a delegate's claim carries."
                ),
            }
        )
        assert "decision" not in (result or {}), (
            "a glyph beside the mark's own name documents the mark rather than claiming"
        )

    def test_a_table_pairing_every_mark_with_its_name_does_not_block(self) -> None:
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
        assert "decision" not in (result or {}), (
            "the plugin must be able to document its own vocabulary in a reply"
        )

    def test_a_skipped_mention_reaches_the_user_in_a_notice(self) -> None:
        line = "The secondhand mark, `[.?]`, is what a delegate's claim carries."
        result = self.decision({"stop_hook_active": False, "last_assistant_message": line})
        assert result is not None, "an exemption a writer can take must not be silent"
        assert line in result["systemMessage"]

    def test_a_bare_mark_still_blocks_on_a_line_documenting_that_same_mark(self) -> None:
        result = self.decision(
            {
                "stop_hook_active": False,
                "last_assistant_message": (
                    "The unsourced mark, `[?]`, says no source is on file, "
                    "and nobody else calls it [?]."
                ),
            }
        )
        assert result is not None, "the exemption covers the code span alone, never the line"
        assert result["decision"] == "block"
        assert "nobody else calls it [?]" in result["reason"]

    def test_a_mark_inside_a_code_span_blocks_when_the_line_names_a_different_mark(self) -> None:
        result = self.decision(
            {
                "stop_hook_active": False,
                "last_assistant_message": (
                    "Unlike the unsourced mark, this count came back from a delegate `[.?]`."
                ),
            }
        )
        assert result is not None, "naming one mark exempts no other mark's glyph"
        assert result["decision"] == "block"
        assert "came back from a delegate" in result["reason"]

    def test_a_mark_inside_a_longer_code_span_does_not_block(self) -> None:
        result = self.decision(
            {
                "stop_hook_active": False,
                "last_assistant_message": (
                    "The rule reads `state the premise marked [?] in the same message`, "
                    "and `MARKS = ('[?]', '[.?]', '[^?]')` names them in the hook."
                ),
            }
        )
        assert result is None, "a span holding code or a quoted rule line stays code"

    def test_a_mark_outside_a_code_span_on_a_line_that_also_mentions_one_blocks(self) -> None:
        result = self.decision(
            {
                "stop_hook_active": False,
                "last_assistant_message": "The `[?]` rule applies here: nobody else calls it [?].",
            }
        )
        assert result is not None, "a real mark beside a quoted one still blocks"
        assert "nobody else calls it [?]." in result["reason"]

    def delegate_decision(self, payload) -> dict | None:
        code, out, err = run_hook(payload, "--delegate", env=self.env)
        assert code == 0, err
        return hook_output(out)

    def delegate_notice(self, result) -> str:
        """The text a SubagentStop pass hands back to the delegate that stopped.

        Nothing a SubagentStop hook returns reaches the caller, so this is the
        one channel the relay group has: the delegate reads it and writes the
        items into the report that does reach the caller.
        """
        assert result is not None, "a delegate pass with something to say must say it"
        assert "decision" not in result, "this pass reports rather than blocks"
        specific = result["hookSpecificOutput"]
        assert specific["hookEventName"] == "SubagentStop"
        return specific["additionalContext"]

    def test_a_delegate_report_carrying_only_a_caret_mark_does_not_block(self) -> None:
        result = self.delegate_decision(
            {
                "stop_hook_active": False,
                "last_assistant_message": "I read the request as covering staging only [^?].",
            }
        )
        assert "decision" not in (result or {}), (
            "a [^?] must ride up to the caller rather than stall the delegate"
        )

    def test_a_delegate_report_carrying_only_a_caret_mark_still_lists_it(self) -> None:
        line = "I read the request as covering staging only [^?]."
        notice = self.delegate_notice(
            self.delegate_decision({"stop_hook_active": False, "last_assistant_message": line})
        )
        assert RELAY_HEADING in notice
        assert line in notice, "a relay-only report is the case the listing exists for"
        assert "Open your report on the question it carries" in notice, (
            "the delegate's own report is what carries the item to the caller"
        )

    def test_a_delegate_relay_listing_reaches_the_delegate_and_the_user_sees_the_same_text(
        self,
    ) -> None:
        result = required(
            self.delegate_decision(
                {
                    "stop_hook_active": False,
                    "last_assistant_message": "I read the request as covering staging only [^?].",
                }
            )
        )
        specific = result["hookSpecificOutput"]
        assert specific["hookEventName"] == "SubagentStop"
        assert result["systemMessage"] == specific["additionalContext"], (
            "a systemMessage reaches the user alone, so it only mirrors what the delegate reads"
        )

    def test_a_delegate_report_blocks_on_a_source_mark(self) -> None:
        result = self.delegate_decision(
            {"stop_hook_active": False, "last_assistant_message": "The count is 12 [?]."}
        )
        assert result is not None, "a delegate resolves the marks it can settle itself"
        assert "The count is 12 [?]." in result["reason"]

    def test_a_delegate_report_scans_its_own_agent_transcript_not_the_shared_session_one(
        self,
    ) -> None:
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
        assert result is None, (
            "a SubagentStop pass must scan the calling agent's own transcript, not the shared session transcript another agent also wrote marks into"
        )

    def test_a_delegate_report_mixing_marks_blocks_and_routes_the_caret_upward(self) -> None:
        result = self.delegate_decision(
            {
                "stop_hook_active": False,
                "last_assistant_message": (
                    "The count is 12 [?].\nI read the request as covering staging only [^?]."
                ),
            }
        )
        assert result is not None
        reason = result["reason"]
        assert RELAY_HEADING in reason
        assert "I read the request as covering staging only [^?]." in reason
        assert "to your caller, with the options" not in reason, (
            "from a delegate the caller's mark takes its carry form, never its resolve form"
        )

    def test_the_main_agent_still_asks_the_user_a_caret_marks_question(self) -> None:
        result = self.decision(
            {
                "stop_hook_active": False,
                "last_assistant_message": "I read the request as covering staging only [^?].",
            }
        )
        assert result is not None, "without --delegate the caret mark keeps its blocking pass"
        assert "to your caller" in result["reason"]
        assert RELAY_HEADING not in result["reason"], "at top level nothing rides up to anyone"

    def test_the_standing_question_blocks_and_routes_to_a_person(self) -> None:
        result = self.decision(
            {
                "stop_hook_active": False,
                "last_assistant_message": "Whether to ship behind a flag is unsettled [!?].",
            }
        )
        assert result is not None, "a [!?] line must block the stop"
        assert result["decision"] == "block"
        assert "Whether to ship behind a flag is unsettled [!?]." in result["reason"]
        assert "to a person" in result["reason"]
        assert "AskUserQuestion" not in result["reason"], (
            "the reader runs on a machine whose toolset this plugin cannot know"
        )

    def test_a_delegate_report_carrying_only_a_standing_question_does_not_block(self) -> None:
        result = self.delegate_decision(
            {
                "stop_hook_active": False,
                "last_assistant_message": "Whether to ship behind a flag is unsettled [!?].",
            }
        )
        assert "decision" not in (result or {}), (
            "a [!?] must ride up to the caller rather than stall the delegate"
        )

    def test_a_delegate_report_says_only_a_person_answers_a_standing_question(self) -> None:
        result = self.delegate_decision(
            {
                "stop_hook_active": False,
                "last_assistant_message": (
                    "The count is 12 [?].\nWhether to ship behind a flag is unsettled [!?]."
                ),
            }
        )
        assert result is not None
        reason = result["reason"]
        assert RELAY_HEADING in reason
        assert "Whether to ship behind a flag is unsettled [!?]." in reason
        assert "only a person answers it" in reason, (
            "the caller may relay this mark and never answer it"
        )

    def test_a_delegate_report_lists_the_callers_mark_apart_from_the_standing_question(
        self,
    ) -> None:
        caller_line = "I read the request as covering staging only [^?]."
        human_line = "Whether to ship behind a flag is unsettled [!?]."
        result = required(
            self.delegate_decision(
                {
                    "stop_hook_active": False,
                    "last_assistant_message": f"The count is 12 [?].\n{caller_line}\n{human_line}",
                }
            )
        )
        reason = result["reason"]
        caller_step = reason.index("\n[^?]\n")
        human_step = reason.index("\n[!?]\n")
        assert caller_step < reason.index("only a person answers it"), (
            "the two carry different acts, and the standing question's is the later one"
        )
        assert caller_step < reason.index(f"- {caller_line}"), (
            "the caller's mark is listed under the instruction naming it"
        )
        assert human_step < reason.index(f"- {human_line}"), (
            "the standing question is listed under its own instruction"
        )
        assert human_line not in reason[caller_step:human_step], (
            "a caller must read the two classes apart, not as one escalation pile"
        )

    def test_a_second_pass_sends_back_a_mark_the_model_was_never_sent(self) -> None:
        result = self.decision(
            {"stop_hook_active": True, "last_assistant_message": "Still marked [?]."}
        )
        assert result is not None, "a mark no pass sent the model reaches it"
        assert result["decision"] == "block", "a systemMessage alone never reaches it"
        assert "- Still marked [?]." in result["reason"]

    def test_a_second_pass_stays_silent_when_no_mark_survives(self) -> None:
        result = self.decision(
            {"stop_hook_active": True, "last_assistant_message": "Every claim carries its source."}
        )
        assert result is None, "a resolved reply draws no notice"

    def test_a_delegate_second_pass_sends_back_claims_its_report_buries(self) -> None:
        lines = "The count is 12 [?].\nThe migration ran on every shard [.?]."
        payload = {"stop_hook_active": False, "agent_id": "agent-one"}
        self.delegate_decision({**payload, "last_assistant_message": lines})
        result = required(
            self.delegate_decision(
                {
                    **payload,
                    "stop_hook_active": True,
                    "last_assistant_message": f"Here is what I found.\n{lines}",
                }
            )
        )
        assert result["decision"] == "block", "the caller reads the report as found"
        assert STANDING_HEADING.format(verb="report") in result["reason"]
        assert "- The count is 12 [?]." in result["reason"]
        assert "- The migration ran on every shard [.?]." in result["reason"]

    def test_a_second_pass_ignores_a_marked_line_the_rewritten_reply_dropped(self) -> None:
        # After a block, the transcript still holds the draft the block asked
        # to rewrite. The second pass judges the rewrite, so a line only the
        # superseded draft carries has already been resolved.
        transcript = self.transcript(
            user_text("do the thing"),
            assistant_text("The endpoint has no other callers [?]."),
            assistant_tool_use(),
            tool_result(),
            assistant_text("The endpoint has no other callers (src/api.py:12)."),
        )
        result = self.decision(
            {
                "stop_hook_active": True,
                "transcript_path": transcript,
                "last_assistant_message": "The endpoint has no other callers (src/api.py:12).",
            }
        )
        assert result is None, "a line the rewrite resolved must not survive the second pass"

    def test_a_delegate_second_pass_stays_silent_on_sent_claims_its_report_opens_on(self) -> None:
        # Every output continues the subagent, which stops again with
        # stop_hook_active still set. Re-sending what it already holds
        # restarts it up to the harness's cap of eight, and each restart can
        # replace the report the caller receives.
        payload = {
            "stop_hook_active": False,
            "agent_id": "agent-one",
            "last_assistant_message": "The count is 12 [?].",
        }
        self.delegate_decision(payload)
        assert self.delegate_decision({**payload, "stop_hook_active": True}) is None, (
            "a claim the delegate was sent and opens its report on goes to it once"
        )

    def test_a_delegate_second_pass_sends_a_claim_it_was_never_sent(self) -> None:
        first = {
            "stop_hook_active": False,
            "agent_id": "agent-one",
            "last_assistant_message": "The count is 12 [?].",
        }
        self.delegate_decision(first)
        result = required(
            self.delegate_decision(
                {
                    **first,
                    "stop_hook_active": True,
                    "last_assistant_message": "The total is 40 [?].",
                }
            )
        )
        assert result["decision"] == "block"
        assert "- The total is 40 [?]." in result["reason"]

    def test_a_delegate_second_pass_sends_the_same_claim_to_another_agent(self) -> None:
        payload = {
            "stop_hook_active": False,
            "agent_id": "agent-one",
            "last_assistant_message": "The count is 12 [?].",
        }
        self.delegate_decision(payload)
        result = required(
            self.delegate_decision({**payload, "stop_hook_active": True, "agent_id": "agent-two"})
        )
        assert "- The count is 12 [?]." in result["reason"], (
            "one agent's record silences no other agent"
        )

    def test_a_main_thread_second_pass_keeps_its_plain_notice(self) -> None:
        result = required(
            self.decision(
                {"stop_hook_active": True, "last_assistant_message": "The count is 12 [?]."}
            )
        )
        assert RELAY_HEADING not in result["systemMessage"], (
            "at top level nothing rides up, so the notice names no relay group"
        )

    def test_a_delegate_first_pass_grounds_an_evidence_mark_rather_than_handing_it_up(self) -> None:
        result = required(
            self.delegate_decision(
                {"stop_hook_active": False, "last_assistant_message": "The count is 12 [?]."}
            )
        )
        reason = result["reason"]
        assert "Gather the evidence" in reason, "a delegate settles what it can settle here"
        assert RELAY_HEADING not in reason, (
            "an evidence mark is the delegate's own to ground, so nothing rides up on it"
        )

    def test_a_main_thread_first_pass_hands_an_evidence_mark_to_nobody(self) -> None:
        result = required(
            self.decision(
                {"stop_hook_active": False, "last_assistant_message": "The count is 12 [?]."}
            )
        )
        assert RELAY_HEADING not in result["reason"], (
            "at top level the reader is the user, who wants the reply and not a debt list"
        )

    def test_a_delegate_second_pass_withholds_a_relay_line_it_already_sent(self) -> None:
        # additionalContext continues the subagent, so re-sending the relay
        # group every pass runs the delegate around the harness's cap of
        # eight consecutive continuations, wastefully for all eight.
        payload = {
            "stop_hook_active": False,
            "agent_id": "agent-one",
            "last_assistant_message": "I read the request as covering staging only [^?].",
        }
        self.delegate_notice(self.delegate_decision(payload))
        result = self.delegate_decision({**payload, "stop_hook_active": True})
        assert result is None, "a relay line re-sent on a second pass is a loop"

    def test_a_delegate_second_pass_sends_a_relay_line_it_never_sent(self) -> None:
        line = "I read the request as covering staging only [^?]."
        payload = {"stop_hook_active": False, "agent_id": "agent-one"}
        self.delegate_decision({**payload, "last_assistant_message": "The count is 12 [?]."})
        notice = self.delegate_notice(
            self.delegate_decision(
                {
                    **payload,
                    "stop_hook_active": True,
                    "last_assistant_message": f"The count is 12 [?].\n{line}",
                }
            )
        )
        assert RELAY_HEADING in notice
        assert line in notice, "a question the delegate was never handed reaches it"


class VerifyMarksBatchHook(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        root = Path(self._tmp.name)
        self.env = isolated_environment(root / "home", state_dir=root / "state")

    def transcript(self, *lines) -> str:
        path = Path(self._tmp.name) / "session.jsonl"
        path.write_text("\n".join(lines) + "\n")
        return str(path)

    def agent_transcript(self, agent_id, *lines, workflow=None) -> str:
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

    def batch(self, transcript, session_id="session-one", **extra) -> dict | None:
        payload = {
            "hook_event_name": "PostToolBatch",
            "session_id": session_id,
            "transcript_path": transcript,
            "tool_calls": [],
        }
        payload.update(extra)
        code, out, err = run_hook(
            payload,
            "--batch",
            env=self.env,
        )
        assert code == 0, err
        return hook_output(out)

    def context_of(self, result) -> str:
        assert result is not None
        assert "decision" not in result, "a batch pass never blocks the loop"
        specific = result["hookSpecificOutput"]
        assert specific["hookEventName"] == "PostToolBatch"
        return specific["additionalContext"]

    def test_batch_reports_a_marked_line_written_earlier_in_the_open_turn(self) -> None:
        transcript = self.transcript(
            user_text("do the thing"),
            assistant_text("The endpoint has no other callers [?]."),
            assistant_tool_use(),
            tool_result(),
        )
        context = self.context_of(self.batch(transcript))
        assert "The endpoint has no other callers [?]." in context

    def test_batch_stays_silent_when_the_open_turn_carries_no_mark(self) -> None:
        transcript = self.transcript(
            user_text("do the thing"),
            assistant_text("Every claim here carries its source."),
            assistant_tool_use(),
            tool_result(),
        )
        assert self.batch(transcript) is None, "an unmarked turn draws no context"

    def test_batch_reports_a_line_once_per_session(self) -> None:
        transcript = self.transcript(
            user_text("do the thing"),
            assistant_text("The endpoint has no other callers [?]."),
            assistant_tool_use(),
            tool_result(),
        )
        assert self.batch(transcript) is not None
        assert self.batch(transcript) is None, (
            "a line already handed back must not repeat on every later batch"
        )

    def test_batch_reports_a_mark_that_appeared_since_the_last_batch(self) -> None:
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
        assert "The migration ran on every shard [.?]." in context
        assert "no other callers" not in context, "the reported line stays reported"

    def test_batch_reports_the_same_line_again_under_a_different_session(self) -> None:
        transcript = self.transcript(
            user_text("do the thing"),
            assistant_text("The endpoint has no other callers [?]."),
        )
        self.batch(transcript, session_id="session-one")
        context = self.context_of(self.batch(transcript, session_id="session-two"))
        assert "The endpoint has no other callers [?]." in context

    def test_batch_routes_a_caret_mark_to_the_caller(self) -> None:
        transcript = self.transcript(
            user_text("do the thing"),
            assistant_text("I read the request as covering staging only [^?]."),
        )
        context = self.context_of(self.batch(transcript))
        assert "I read the request as covering staging only [^?]." in context
        assert "to your caller" in context
        assert "AskUserQuestion" not in context, (
            "the reader runs on a machine whose toolset this plugin cannot know"
        )

    def test_batch_reports_a_delegates_own_mark_from_its_own_transcript(self) -> None:
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
        assert "The KV-cache holds every shard [?]." in context
        assert "orchestrator's own claim" not in context, (
            "a delegate must not be handed a mark the orchestrator wrote"
        )

    def test_batch_reports_a_workflow_delegates_mark_from_its_nested_transcript(self) -> None:
        transcript = self.transcript(user_text("do the thing"))
        self.agent_transcript(
            "three",
            user_text("do the shard task"),
            assistant_text("The shard count is 12 [?]."),
            workflow="wf_9f8f2559",
        )
        context = self.context_of(self.batch(transcript, agent_id="three"))
        assert "The shard count is 12 [?]." in context

    def test_batch_stays_silent_when_a_delegate_has_no_transcript_of_its_own(self) -> None:
        transcript = self.transcript(
            user_text("do the thing"),
            assistant_text("The orchestrator's own claim stands unverified [?]."),
        )
        assert self.batch(transcript, agent_id="absent") is None, (
            "with no transcript of its own a delegate draws nothing, rather than falling back to the shared session file"
        )

    def test_batch_keeps_a_delegates_ledger_apart_from_the_main_threads(self) -> None:
        line = "The endpoint has no other callers [?]."
        transcript = self.transcript(user_text("do the thing"), assistant_text(line))
        self.agent_transcript("two", user_text("do the sub task"), assistant_text(line))
        assert self.batch(transcript, agent_id="two") is not None
        context = self.context_of(self.batch(transcript))
        assert line in context, (
            "a delegate's ledger must not suppress the same sentence for the main thread"
        )

    def test_a_subagent_batch_leaves_the_main_threads_report_standing(self) -> None:
        transcript = self.transcript(
            user_text("do the thing"),
            assistant_text("The endpoint has no other callers [?]."),
        )
        self.batch(transcript, agent_id="agent-two")
        context = self.context_of(self.batch(transcript))
        assert "The endpoint has no other callers [?]." in context, (
            "a subagent's batch must not record a line the main thread never heard about"
        )

    def test_batch_stays_silent_without_a_readable_transcript(self) -> None:
        code, out, err = run_hook(
            {"hook_event_name": "PostToolBatch", "session_id": "session-one"},
            "--batch",
            env=self.env,
        )
        assert code == 0, err
        assert out.strip() == "", "no transcript means nothing to scan"


if __name__ == "__main__":
    unittest.main()
