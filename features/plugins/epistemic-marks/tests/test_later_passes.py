"""Tests for what reaches the model on every pass of every verify-marks event.

    python3 -m unittest discover -s tests -p test_later_passes.py -v

A `systemMessage` reaches the user and never the model, per
https://code.claude.com/docs/en/hooks. So every output carries a field the
model reads, and its `systemMessage` only mirrors that text. A later Stop pass,
the one arriving with stop_hook_active set, blocks on any marked line the
model was never sent and on any line it was sent but the reply does not open
on. It stays silent only about lines the model already holds.

Each test drives the entrypoint through stdin the way the harness does, with
the state directory, HOME, XDG directories and git config all pointed into a
temporary directory.
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from epistemic_marks.messages import STANDING_HEADING

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = PLUGIN_ROOT / "hooks" / "verify-marks.py"

FIRST = "The parser keeps three tests [?]."
SECOND = "The vendor said the flag is gone [.?]."
THIRD = "The cache key covers the lockfile [?]."
CALLER = "I read the request as covering staging only [^?]."
MENTION = "The unsourced mark, `[?]`, ends a clause nobody sourced."
GUESS = "I suspect the cache went stale."
PROSE = "Here is what I found."


def model_text(result) -> str:
    """The text the model reads in one hook output, failing where there is none."""
    if "decision" in result:
        assert result["decision"] == "block"
        return result["reason"]
    specific = result.get("hookSpecificOutput") or {}
    if "additionalContext" in specific:
        return specific["additionalContext"]
    if specific.get("permissionDecision") == "deny":
        return specific["permissionDecisionReason"]
    message = f"an output reaches the user alone: {result}"
    raise AssertionError(message)


class HookCase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        root = Path(self._tmp.name)
        home = root / "home"
        home.mkdir()
        inherited = {
            key: value
            for key, value in os.environ.items()
            if key not in ("VERIFY_MARKS_STATE_DIR", "CLAUDE_PLUGIN_DATA")
            and not key.startswith(("XDG_", "GIT_"))
        }
        self.env = {
            **inherited,
            "HOME": str(home),
            "XDG_CONFIG_HOME": str(home / ".config"),
            "XDG_DATA_HOME": str(home / ".local" / "share"),
            "XDG_STATE_HOME": str(home / ".local" / "state"),
            "XDG_CACHE_HOME": str(home / ".cache"),
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_CONFIG_NOSYSTEM": "1",
            "VERIFY_MARKS_STATE_DIR": str(root / "state"),
        }

    def hook(self, payload, *args) -> dict | None:
        completed = subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            input=json.dumps(payload),
            capture_output=True,
            text=True,
            check=False,
            env=self.env,
            timeout=8,
        )
        assert completed.returncode == 0, completed.stderr
        result = json.loads(completed.stdout) if completed.stdout.strip() else None
        if result is not None:
            text = model_text(result)
            assert result.get("systemMessage") == text, "the user sees what the model was sent"
        return result

    def stop(self, message, *, again, key="session-one", delegate=False) -> dict | None:
        payload = {
            "stop_hook_active": again,
            "last_assistant_message": message,
            ("agent_id" if delegate else "session_id"): key,
        }
        return self.hook(payload, *(["--delegate"] if delegate else []))

    def assert_blocks_on(self, result, line) -> None:
        assert result is not None, "a finding the model was never sent went unreported"
        assert result.get("decision") == "block", "the finding never reached the model"
        assert f"- {line}" in result["reason"]


class EveryOutputReachesTheModel(HookCase):
    """Each event and pass, on text that draws output, passes through `hook`'s check."""

    def test_every_stop_and_subagent_stop_pass(self) -> None:
        messages = (
            FIRST,
            f"{PROSE}\n{FIRST}",
            GUESS,
            MENTION,
            CALLER,
            f"{FIRST}\n{CALLER}\n{MENTION}",
        )
        for delegate in (False, True):
            for message in messages:
                for again in (False, True):
                    with self.subTest(delegate=delegate, message=message, again=again):
                        key = f"{delegate}-{message}-{again}"
                        self.stop(message, again=False, key=key, delegate=delegate)
                        if again:
                            self.stop(message, again=True, key=key, delegate=delegate)

    def test_the_batch_pass(self) -> None:
        transcript = Path(self._tmp.name) / "session.jsonl"
        transcript.write_text(
            json.dumps({"type": "user", "message": {"role": "user", "content": "go"}})
            + "\n"
            + json.dumps(
                {
                    "type": "assistant",
                    "message": {"role": "assistant", "content": [{"type": "text", "text": FIRST}]},
                }
            )
            + "\n"
        )
        payload = {
            "hook_event_name": "PostToolBatch",
            "session_id": "session-one",
            "transcript_path": str(transcript),
            "tool_calls": [],
        }
        assert self.hook(payload, "--batch") is not None
        assert self.hook(payload, "--batch") is None, "a line the model holds goes once"

    def test_the_spawn_prompt_pass(self) -> None:
        result = self.hook({"tool_input": {"prompt": GUESS}}, "--prompt")
        assert result["hookSpecificOutput"]["permissionDecision"] == "deny"


class ATopLevelLaterPass(HookCase):
    def test_a_mark_first_written_after_the_block_blocks(self) -> None:
        self.assert_blocks_on(self.stop(FIRST, again=False), FIRST)
        result = self.stop(f"{FIRST}\n{SECOND}", again=True)
        self.assert_blocks_on(result, SECOND)
        assert f"- {FIRST}" not in result["reason"], "the reply opens on what it was sent"

    def test_every_later_pass_with_a_mark_never_sent_blocks_not_only_the_second(self) -> None:
        self.stop(FIRST, again=False)
        self.assert_blocks_on(self.stop(f"{FIRST}\n{SECOND}", again=True), SECOND)
        self.assert_blocks_on(self.stop(f"{FIRST}\n{SECOND}\n{THIRD}", again=True), THIRD)

    def test_a_sent_mark_below_unmarked_text_blocks_with_the_opening_act(self) -> None:
        # The live miss: the rewrite kept its marks under a summary, and the
        # notice listing them went to the user while the turn ended.
        self.stop(FIRST, again=False)
        for attempt in range(3):
            with self.subTest(attempt=attempt):
                result = self.stop(f"{PROSE}\n{FIRST}", again=True)
                self.assert_blocks_on(result, FIRST)
                assert STANDING_HEADING.format(verb="reply") in result["reason"]

    def test_a_sent_mark_opening_the_reply_ends_the_loop_in_silence(self) -> None:
        self.stop(FIRST, again=False)
        for opening in (FIRST, f"# Unverified\n\n{FIRST}\n\n{PROSE}", f"**Still open:**\n{FIRST}"):
            with self.subTest(opening=opening):
                assert self.stop(opening, again=True) is None, "the model holds this already"

    def test_a_mention_reaches_the_model_once(self) -> None:
        result = self.stop(MENTION, again=False)
        assert "decision" not in result, "a mention claims nothing, so it never blocks"
        assert MENTION in result["hookSpecificOutput"]["additionalContext"]
        assert result["hookSpecificOutput"]["hookEventName"] == "Stop"
        assert self.stop(MENTION, again=True) is None, "the model holds this mention already"

    def test_a_mark_written_after_another_hook_continued_the_turn_blocks(self) -> None:
        # A clean first pass draws nothing from this plugin, so the next stop
        # arrives with stop_hook_active set only because some other Stop hook
        # sent the model back.
        assert self.stop("Every claim carries its source.", again=False) is None
        self.assert_blocks_on(self.stop(FIRST, again=True), FIRST)

    def test_a_new_turn_forgets_what_the_last_turn_sent(self) -> None:
        self.stop(FIRST, again=False)
        assert self.stop("Every claim carries its source.", again=False) is None
        self.assert_blocks_on(self.stop(FIRST, again=True), FIRST)

    def test_one_sessions_record_silences_no_other_session(self) -> None:
        self.stop(FIRST, again=False, key="session-one")
        self.assert_blocks_on(self.stop(FIRST, again=True, key="session-two"), FIRST)

    def test_without_a_writable_state_directory_every_pass_sends_every_line(self) -> None:
        blocker = Path(self._tmp.name) / "a-file"
        blocker.write_text("")
        self.env["VERIFY_MARKS_STATE_DIR"] = str(blocker / "state")
        self.assert_blocks_on(self.stop(FIRST, again=False), FIRST)
        self.assert_blocks_on(self.stop(FIRST, again=True), FIRST)


class ADelegateLaterPass(HookCase):
    def test_a_mark_first_written_after_the_block_blocks(self) -> None:
        self.stop(FIRST, again=False, key="agent-one", delegate=True)
        result = self.stop(f"{FIRST}\n{THIRD}", again=True, key="agent-one", delegate=True)
        self.assert_blocks_on(result, THIRD)
        assert f"- {FIRST}" not in result["reason"]

    def test_a_sent_mark_below_unmarked_text_blocks_with_the_opening_act(self) -> None:
        self.stop(FIRST, again=False, key="agent-one", delegate=True)
        result = self.stop(f"{PROSE}\n{FIRST}", again=True, key="agent-one", delegate=True)
        self.assert_blocks_on(result, FIRST)
        assert STANDING_HEADING.format(verb="report") in result["reason"]

    def test_a_relay_line_written_later_reaches_the_delegate_without_a_block(self) -> None:
        self.stop(FIRST, again=False, key="agent-one", delegate=True)
        result = self.stop(f"{FIRST}\n{CALLER}", again=True, key="agent-one", delegate=True)
        assert "decision" not in result, "a delegate cannot settle its caller's question"
        assert CALLER in result["hookSpecificOutput"]["additionalContext"]


if __name__ == "__main__":
    unittest.main()
