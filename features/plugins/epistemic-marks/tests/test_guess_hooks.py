"""Tests for what the hooks do about a guess written in words, on every surface.

    uv run --no-project --python 3.14 python -m unittest discover -s tests -p test_guess_hooks.py -v

README.md lists what counts as a guess in words and what passes: wording of
doubt, a status written as a sentence or a label, and a sentence building on a
marked or guessed claim are flagged; a mark or a source in the sentence, code,
quoted text, block quotes and questions pass; "may", "should" and "must" are
left alone outside a few fixed phrases. A guess reaches a reader through a
reply, a delegate's report, text written mid-turn, or a prompt composed for a
delegate. Each test drives the entrypoint through stdin the way the harness
does, on fixtures built in a temporary directory.
"""

import json
import tempfile
import unittest
from pathlib import Path

from support import (
    PLUGIN_ROOT,
    assistant_text,
    hook_output,
    isolated_environment,
    required,
    run_hook,
    user_text,
)

INCIDENT_GUESS = (
    "My unconfirmed guess is that files in the lane worktrees fall into a project "
    "the editor builds without that config."
)
INCIDENT_REST = (
    "That would leave them without the claude-code path, Node types or JSX settings, "
    "which matches the errors."
)
INCIDENT = f"{INCIDENT_GUESS} {INCIDENT_REST}"
STALE = "I suspect the cache went stale."

# Sentences the README names as a guess in words, each with nothing else in it.
FLAGGED = (
    "My guess is the cache went stale.",
    STALE,
    "The cache is probably stale.",
    "It seems the watcher holds the file open.",
    "That should fix it.",
    "As far as I know the flag landed in version 3.",
    "I haven't checked this, but the watcher holds the file open.",
    "The watcher holds the file open (unverified).",
    "I haven't read any code, so all three are guesses.",
    "The lockfile drifted [?]. That would break the install.",
    "The lockfile drifted [?]. So the install fails on CI.",
    INCIDENT,
    'The message read "the cache\nis stale" and I suspect it is right.',
)

# Sentences the README says pass: a mark or a source, code, quoted text, a
# block quote, a question, and modals that give permission or state a requirement.
PASSING = (
    "The docs say the value may be null (https://example.com/api#value).",
    "The cache is probably stale (src/cache.py:12).",
    "The log reads:\n\n```\nprobably stale, I think\n```\n\nI ran it twice.",
    "The flag `--probably` goes unused.",
    'The writer used "unconfirmed guess" as the claim\'s status.',
    "> My guess is that the cache went stale.",
    "Is the cache probably stale?",
    "You may change the tests and the README.",
    "The function should return a list.",
    "It must be the first argument.",
    'The message read "My guess is the cache is\nprobably stale. That would explain it." and no more.',
)

# A mark ends the guess in words, so a prompt carrying one passes.
MARKED_PROMPTS = (
    "The cache is probably stale [?]. Confirm it.",
    "The lockfile drifted [?]. That would break the install [?]. Confirm both.",
)


class HookCase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        root = Path(self._tmp.name)
        self.env = isolated_environment(root / "home", state_dir=root / "state")

    def run_hook(self, payload, *args, in_process=False) -> dict | None:
        code, out, err = run_hook(payload, *args, env=self.env, in_process=in_process)
        assert code == 0, f"{out}{err}"
        return hook_output(out)

    def stop(self, message, *, again=False, delegate=False, **extra) -> dict | None:
        payload = {"stop_hook_active": again, "last_assistant_message": message, **extra}
        return self.run_hook(payload, *(["--delegate"] if delegate else []), in_process=True)

    def transcript(self, *texts) -> str:
        path = Path(self._tmp.name) / "session.jsonl"
        lines = [user_text("do the thing"), *(assistant_text(text) for text in texts)]
        path.write_text("\n".join(lines) + "\n")
        return str(path)


class AReplyGuessingInWordsIsSentBack(HookCase):
    def test_a_guess_in_words_blocks_and_a_sentence_that_passes_does_not(self) -> None:
        for line in FLAGGED:
            with self.subTest(flagged=line):
                result = required(self.stop(line, session_id=line))
                assert result["decision"] == "block", "wording stood in for the mark"
                assert line.split(". ")[-1].rstrip(".").split("\n")[-1] in result["reason"]
        for line in PASSING:
            with self.subTest(passing=line):
                assert self.stop(line, session_id=line) is None, "the scan fired where none was due"

    def test_the_incident_lists_the_guess_and_the_sentence_resting_on_it(self) -> None:
        result = required(self.stop(INCIDENT))
        assert INCIDENT_GUESS in result["reason"]
        assert INCIDENT_REST in result["reason"]

    def test_a_guess_and_a_mark_arrive_in_one_block(self) -> None:
        result = required(self.stop(f"The count is 12 [?].\n\n{STALE}"))
        assert result["decision"] == "block"
        assert "- The count is 12 [?]." in result["reason"]
        assert f"- {STALE}" in result["reason"]

    def test_a_guess_written_before_the_final_message_blocks_the_stop(self) -> None:
        result = required(self.stop("Done.", transcript_path=self.transcript(STALE)))
        assert STALE in result["reason"]

    def test_a_guess_still_in_the_rewrite_blocks_again_every_time(self) -> None:
        for attempt in range(3):
            with self.subTest(attempt=attempt):
                result = required(self.stop(STALE, again=True))
                assert result["decision"] == "block", "a guess left standing got through"
                assert f"- {STALE}" in result["reason"]

    def test_a_rewrite_with_the_guess_marked_ends_the_loop(self) -> None:
        assert required(self.stop(STALE))["decision"] == "block"
        assert required(self.stop("The cache went stale [?].", again=True))["decision"] == "block"
        assert self.stop("The cache went stale [?].", again=True) is None, (
            "a mark opening the reply stands"
        )


class ADelegateReportGuessingInWordsIsSentBack(HookCase):
    def test_the_first_pass_and_every_later_pass_block(self) -> None:
        for again in (False, True, True, True):
            with self.subTest(again=again):
                result = required(self.stop(INCIDENT, again=again, delegate=True, agent_id="a1"))
                assert result["decision"] == "block", "a caller acts on the report as found"
                assert INCIDENT_GUESS in result["reason"]
                assert INCIDENT_REST in result["reason"]


class AGuessWrittenMidTurnIsHandedBackOnce(HookCase):
    def batch(self, transcript) -> dict | None:
        return self.run_hook(
            {
                "hook_event_name": "PostToolBatch",
                "session_id": "session-one",
                "transcript_path": transcript,
                "tool_calls": [],
            },
            "--batch",
        )

    def test_the_guess_reaches_the_agent_before_its_next_step_once_per_session(self) -> None:
        transcript = self.transcript(INCIDENT)
        specific = required(self.batch(transcript))["hookSpecificOutput"]
        assert specific["hookEventName"] == "PostToolBatch"
        assert INCIDENT_GUESS in specific["additionalContext"]
        assert INCIDENT_REST in specific["additionalContext"]
        assert self.batch(transcript) is None, "a line already reported is not reported again"


class APromptHandingADelegateAGuessIsDenied(HookCase):
    def prompt(self, text, tool="Agent") -> dict | None:
        return self.run_hook(
            {
                "hook_event_name": "PreToolUse",
                "tool_name": tool,
                "tool_input": {"description": "probably fine", "prompt": text},
            },
            "--prompt",
        )

    def reason_of(self, result) -> str:
        specific = required(result)["hookSpecificOutput"]
        assert specific["hookEventName"] == "PreToolUse"
        assert specific["permissionDecision"] == "deny"
        return specific["permissionDecisionReason"]

    def test_a_guess_in_the_prompt_denies_the_call_and_names_only_the_guess(self) -> None:
        reason = self.reason_of(
            self.prompt(f"Fix the editor errors in the lane worktrees. {INCIDENT}")
        )
        assert INCIDENT_GUESS in reason
        assert INCIDENT_REST in reason
        assert "Fix the editor errors" not in reason

    def test_a_cause_a_user_attribution_or_a_leading_question_handed_over_as_fact_is_denied(
        self,
    ) -> None:
        # Each came from a session told to get a guess past this hook. The
        # README's list leaves these forms open, so they stay as the code
        # treats them.
        for text in (
            "The flaky test fails because two tests share a temp directory. Fix it.",
            "As the user said, the two tests share a temp dir. Give each its own.",
            "Did the cache key change, so every run reinstalls? Fix the key.",
        ):
            with self.subTest(text=text):
                assert self.reason_of(self.prompt(text))

    def test_a_marked_observation_and_plain_instructions_pass(self) -> None:
        for text in (
            *MARKED_PROMPTS,
            "You may change the tests. The suite should pass before the merge.\n"
            'Report your hunch only as a marked claim, never as "my guess".\n'
            "Is the cache likely stale? Read `src/cache.py` and say what you found.",
        ):
            with self.subTest(text=text):
                assert self.prompt(text) is None, "an instruction is no guess"


class TheWiringCoversEverySurface(unittest.TestCase):
    def setUp(self) -> None:
        self.wiring = json.loads((PLUGIN_ROOT / "hooks" / "hooks.json").read_text())["hooks"]

    def test_a_composed_prompt_is_checked_before_either_spawn_tool_runs(self) -> None:
        matchers = self.wiring.get("PreToolUse", [])
        for tool in ("Agent", "Task"):
            with self.subTest(tool=tool):
                assert [
                    matcher
                    for matcher in matchers
                    if tool in matcher.get("matcher", "").split("|")
                    and any(
                        "verify-marks.py" in hook["command"] and "--prompt" in hook["command"]
                        for hook in matcher["hooks"]
                    )
                ], f"no hook reads a prompt handed to {tool}"

    def test_every_hook_is_a_local_command_and_no_hook_calls_a_model(self) -> None:
        for event, matchers in self.wiring.items():
            for matcher in matchers:
                for hook in matcher["hooks"]:
                    with self.subTest(event=event):
                        assert hook["type"] == "command"


if __name__ == "__main__":
    unittest.main()
