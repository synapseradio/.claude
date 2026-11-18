"""Tests for the verify-marks hook on a mark in a reply, a delegate report, and an open turn.

    python3 -m unittest discover -s tests -p test_verify_marks.py -v

Each test drives the entrypoint through stdin the way the harness does, with
every fixture built in a temporary directory under an isolated environment.
The stories come from README.md: the Stop hook sends back a reply ending on a
mark, the SubagentStop hook leaves the caller's mark and the standing question
for the delegate to carry up, and the PostToolBatch hook shows each marked
line once per session and never blocks.
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

TOKENS = ("[?]", "[.?]", "[^?]", "[!?]")


def tool_result() -> str:
    return entry("user", [{"type": "tool_result", "tool_use_id": "t1", "content": "ok"}])


def assistant_tool_use() -> str:
    return entry("assistant", [{"type": "tool_use", "id": "t1", "name": "Read", "input": {}}])


class HookCase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        self.env = isolated_environment(self.root / "home", state_dir=self.root / "state")

    def transcript(self, *lines, name="session.jsonl") -> str:
        path = self.root / name
        path.write_text("\n".join(lines) + "\n")
        return str(path)

    def run_pass(self, payload, *args) -> dict | None:
        code, out, err = run_hook(payload, *args, env=self.env)
        assert code == 0, err
        return hook_output(out)

    def stop(self, message, *, delegate=False, **extra) -> dict | None:
        payload = {"stop_hook_active": False, "last_assistant_message": message, **extra}
        return self.run_pass(payload, *(["--delegate"] if delegate else []))


class AReplyEndingOnAMarkIsSentBack(HookCase):
    def test_each_mark_blocks_the_stop_and_lists_its_line(self) -> None:
        for token in TOKENS:
            with self.subTest(mark=token):
                line = f"The endpoint has no other callers {token}."
                result = required(self.stop(line))
                assert result["decision"] == "block"
                assert line in result["reason"]

    def test_only_the_turn_since_the_last_user_message_is_read(self) -> None:
        transcript = self.transcript(
            user_text("earlier question"),
            assistant_text("Old reply, still unverified [?]."),
            user_text("do the thing"),
            assistant_text("The endpoint has no other callers [?]."),
            assistant_tool_use(),
            tool_result(),
        )
        result = required(self.stop("Done.", transcript_path=transcript))
        assert result["decision"] == "block"
        assert "The endpoint has no other callers [?]." in result["reason"]
        assert "Old reply" not in result["reason"]


class AMarkThatIsCodeOrTalkAboutAMarkDoesNotBlock(HookCase):
    """README.md: fenced code, a longer code span, and a line naming the mark do not count."""

    def test_which_marks_count(self) -> None:
        in_words = "The unsourced mark, `[?]`, says no source is on file"
        # (label, reply, blocks, line named in the notice the user sees)
        rows = (
            (
                "a fenced block",
                "Here it is:\n```\nmark it `[?]` when no source exists\n```\nThat is all.",
                False,
                False,
            ),
            (
                "a longer code span",
                "The rule reads `state the premise marked [?] in the same message`.",
                False,
                False,
            ),
            (
                "a glyph in a code span beside its own name",
                "The secondhand mark, `[.?]`, is what a delegate's claim carries.",
                False,
                True,
            ),
            (
                "a glyph straight after its own name",
                "That sentence needed the unsourced mark [?] at the end of its first clause.",
                False,
                True,
            ),
            (
                "a quoted glyph beside its own name",
                'The unsourced mark, "[?]", was missing from that sentence.',
                False,
                True,
            ),
            (
                "a table pairing each mark with its name",
                "| Mark | Name |\n| --- | --- |\n| `[?]` | the unsourced mark |\n"
                "| `[.?]` | the secondhand mark |\n",
                False,
                False,
            ),
            (
                "a quoted run holding a mark",
                'The session wrote "the cache is stale [?]" and stopped.',
                False,
                False,
            ),
            (
                "a glyph in a code span on a line that names no mark",
                "That count came back from the background agent at 146 test files `[.?]`.",
                True,
                False,
            ),
            (
                "a glyph in a code span beside a different mark's name",
                "Unlike the unsourced mark, this count came back from a delegate `[.?]`.",
                True,
                False,
            ),
            (
                "a bare mark on a line documenting the same mark",
                f"{in_words}, and nobody else calls it [?].",
                True,
                False,
            ),
            (
                "a bare mark beside a quoted one",
                "The `[?]` rule applies here: nobody else calls it [?].",
                True,
                False,
            ),
        )
        for label, reply, blocks, noticed in rows:
            with self.subTest(label):
                result = self.stop(reply)
                if blocks:
                    assert required(result)["decision"] == "block"
                else:
                    assert "decision" not in (result or {}), "a mark that is no claim blocked"
                if noticed:
                    assert reply in required(result)["systemMessage"], (
                        "the exemption must stay visible to the user"
                    )


class ADelegateReportCarriesRelayedMarksUp(HookCase):
    CALLER = "I read the request as covering staging only [^?]."
    PERSON = "Whether to ship behind a flag is unsettled [!?]."

    def test_the_callers_mark_and_the_standing_question_do_not_block_and_are_listed(self) -> None:
        for line in (self.CALLER, self.PERSON):
            with self.subTest(line=line):
                result = required(self.stop(line, delegate=True))
                assert "decision" not in result, "a relayed mark must not stall the delegate"
                specific = result["hookSpecificOutput"]
                assert specific["hookEventName"] == "SubagentStop"
                assert line in specific["additionalContext"]

    def test_a_mark_the_delegate_can_settle_blocks_and_the_relayed_marks_ride_along(self) -> None:
        settle = "The count is 12 [?]."
        result = required(self.stop(f"{settle}\n{self.CALLER}\n{self.PERSON}", delegate=True))
        assert result["decision"] == "block"
        for line in (settle, self.CALLER, self.PERSON):
            assert line in result["reason"]

    def test_a_delegate_is_judged_on_its_own_transcript_and_not_the_sessions(self) -> None:
        session = self.transcript(
            user_text("earlier orchestrator turn"),
            assistant_text("A sibling agent's finding stands unverified [?]."),
        )
        own = self.transcript(
            user_text("do the KV-cache task"),
            assistant_text("The KV-cache fits comfortably, source verified."),
            name="agent-this-one.jsonl",
        )
        result = self.stop(
            "The KV-cache fits comfortably, source verified.",
            delegate=True,
            transcript_path=session,
            agent_transcript_path=own,
        )
        assert result is None, "a delegate was handed a mark the orchestrator wrote"


class ABatchShowsEachMarkedLineOnceAndNeverBlocks(HookCase):
    def batch(self, transcript, session_id="session-one", **extra) -> dict | None:
        payload = {
            "hook_event_name": "PostToolBatch",
            "session_id": session_id,
            "transcript_path": transcript,
            **extra,
        }
        result = self.run_pass(payload, "--batch")
        assert "decision" not in (result or {}), "a batch pass never blocks the loop"
        return result

    def context_of(self, result) -> str:
        specific = required(result)["hookSpecificOutput"]
        assert specific["hookEventName"] == "PostToolBatch"
        return specific["additionalContext"]

    def test_a_line_is_shown_once_per_session_and_a_later_one_is_shown_when_written(self) -> None:
        first = "The endpoint has no other callers [?]."
        later = "The migration ran on every shard [.?]."
        unmarked = self.transcript(user_text("do the thing"), assistant_text("All sourced."))
        assert self.batch(unmarked) is None, "an unmarked turn draws no context"

        opening = (user_text("do the thing"), assistant_text(first), assistant_tool_use())
        assert first in self.context_of(self.batch(self.transcript(*opening)))
        assert self.batch(self.transcript(*opening)) is None, "a shown line must not repeat"

        grown = self.transcript(*opening, tool_result(), assistant_text(later))
        context = self.context_of(self.batch(grown))
        assert later in context
        assert first not in context, "the shown line stays shown"

        assert first in self.context_of(self.batch(self.transcript(*opening), "session-two")), (
            "a new session starts with nothing shown"
        )

    def test_a_delegate_is_shown_its_own_marks_and_the_main_thread_keeps_its_own(self) -> None:
        orchestrator = "The orchestrator's own claim stands unverified [?]."
        delegate = "The KV-cache holds every shard [?]."
        session = self.transcript(user_text("do the thing"), assistant_text(orchestrator))
        subagents = self.root / "session" / "subagents"
        subagents.mkdir(parents=True)
        (subagents / "agent-two.jsonl").write_text(
            "\n".join([user_text("do the KV-cache task"), assistant_text(delegate)]) + "\n"
        )

        context = self.context_of(self.batch(session, agent_id="two"))
        assert delegate in context
        assert orchestrator not in context, "a delegate must not be handed the orchestrator's mark"

        main = self.context_of(self.batch(session))
        assert orchestrator in main, "a delegate's batch must not use up the main thread's lines"
        assert delegate not in main


if __name__ == "__main__":
    unittest.main()
