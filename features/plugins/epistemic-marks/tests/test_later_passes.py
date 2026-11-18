"""Tests for the passes after a block: a mark shown to the user ends the reply, a new one is sent back.

    python3 -m unittest discover -s tests -p test_later_passes.py -v

README.md: a reply ending on a mark is sent back once, a mark left after the
rewrite is shown to the user and the reply ends, and a delegate leaves its
caller's mark in the report for the caller. A `systemMessage` reaches the user
and never the model, so every output carries a field the model reads. The
harness ends a turn its hooks have continued eight times, so a stream of fresh
marks stops blocking before that.
"""

import tempfile
import unittest
from pathlib import Path

from support import hook_output, isolated_environment, required, run_hook

FIRST = "The parser keeps three tests [?]."
SECOND = "The vendor said the flag is gone [.?]."
CALLER = "I read the request as covering staging only [^?]."
MENTION = "The unsourced mark, `[?]`, ends a clause nobody sourced."
GUESS = "I suspect the cache went stale."
PROSE = "Here is what I found."
HARNESS_CONTINUATION_LIMIT = 8


def model_text(result) -> str:
    """The text the model reads in one hook output, failing where there is none."""
    if "decision" in result:
        assert result["decision"] == "block"
        return result["reason"]
    specific = result.get("hookSpecificOutput") or {}
    if "additionalContext" in specific:
        return specific["additionalContext"]
    message = f"an output reaches the user alone: {result}"
    raise AssertionError(message)


class HookCase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        root = Path(self._tmp.name)
        self.env = isolated_environment(root / "home", state_dir=root / "state")

    def stop(
        self, message, *, again, key="session-one", delegate=False, in_process=False
    ) -> dict | None:
        payload = {
            "stop_hook_active": again,
            "last_assistant_message": message,
            ("agent_id" if delegate else "session_id"): key,
        }
        code, stdout, stderr = run_hook(
            payload,
            *(["--delegate"] if delegate else []),
            env=self.env,
            in_process=in_process,
        )
        assert code == 0, f"{stdout}{stderr}"
        return hook_output(stdout)

    def assert_blocks_on(self, result, line) -> None:
        assert result is not None, "a finding the model was never sent went unreported"
        assert result.get("decision") == "block", "the finding never reached the model"
        assert f"- {line}" in result["reason"]


class EveryOutputReachesTheModel(HookCase):
    def test_every_stop_and_subagent_stop_output_carries_a_field_the_model_reads(self) -> None:
        messages = (FIRST, f"{PROSE}\n{FIRST}", GUESS, MENTION, CALLER, f"{FIRST}\n{CALLER}")
        for delegate in (False, True):
            for message in messages:
                for again in (False, True):
                    with self.subTest(delegate=delegate, message=message, again=again):
                        key = f"{delegate}-{message}-{again}"
                        result = self.stop(
                            message, again=False, key=key, delegate=delegate, in_process=True
                        )
                        if again:
                            result = self.stop(
                                message, again=True, key=key, delegate=delegate, in_process=True
                            )
                        if result is not None:
                            model_text(result)


class ALaterPassAfterABlock(HookCase):
    def test_a_mark_the_reply_still_opens_on_ends_the_loop_and_one_buried_is_sent_back(
        self,
    ) -> None:
        self.assert_blocks_on(self.stop(FIRST, again=False), FIRST)
        for opening in (FIRST, f"# Unverified\n\n{FIRST}\n\n{PROSE}"):
            with self.subTest(opening=opening):
                assert self.stop(opening, again=True) is None, "the model holds this already"
        self.assert_blocks_on(self.stop(f"{PROSE}\n{FIRST}", again=True), FIRST)

    def test_a_mark_first_written_after_the_block_is_sent_back(self) -> None:
        self.assert_blocks_on(self.stop(FIRST, again=False), FIRST)
        self.assert_blocks_on(self.stop(f"{FIRST}\n{SECOND}", again=True), SECOND)

    def test_a_resolved_rewrite_draws_nothing(self) -> None:
        self.assert_blocks_on(self.stop(FIRST, again=False), FIRST)
        assert self.stop("Every claim carries its source.", again=True) is None

    def test_a_bullet_added_to_a_line_the_listing_quoted_ends_the_loop(self) -> None:
        # The listing quotes each line as an item, so an agent copying a
        # bulleted claim from it writes the quote's bullet ahead of its own.
        bulleted = "- **Request matched description:** the spec says so [?]"
        first = required(self.stop(bulleted, again=False))
        copied = next(line for line in first["reason"].splitlines() if "Request matched" in line)
        for attempt in range(3):
            with self.subTest(attempt=attempt):
                assert self.stop(copied, again=True) is None, "the copy adds only a bullet"
                copied = f"- {copied}"

    def test_fresh_marks_stop_blocking_before_the_harness_gives_up_on_the_turn(self) -> None:
        written = []
        for index in range(HARNESS_CONTINUATION_LIMIT):
            written.append(f"Claim {index} holds [?].")
            result = required(self.stop("\n".join(written), again=index > 0))
            if "decision" not in result:
                assert f"- {written[-1]}" in result["hookSpecificOutput"]["additionalContext"], (
                    "a finding past the last block must still reach the model"
                )
                return
        self.fail("every pass blocked, so the turn runs until the harness ends it")


class ADelegateLaterPass(HookCase):
    def test_a_relayed_mark_is_sent_once_and_without_a_block(self) -> None:
        self.stop(FIRST, again=False, key="agent-one", delegate=True)
        result = required(
            self.stop(f"{FIRST}\n{CALLER}", again=True, key="agent-one", delegate=True)
        )
        assert "decision" not in result, "a delegate cannot settle its caller's question"
        assert CALLER in result["hookSpecificOutput"]["additionalContext"]
        assert self.stop(CALLER, again=True, key="agent-one", delegate=True) is None, (
            "a relay line sent twice runs the delegate around the harness's limit"
        )


if __name__ == "__main__":
    unittest.main()
