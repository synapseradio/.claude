"""Tests for what the hooks do about a guess written in words, on every surface.

    python3 -m unittest discover -s tests -p test_guess_hooks.py -v

A guess reaches a reader through a reply, a delegate's report, text written
mid-turn, or a prompt composed for a delegate. Each test drives the entrypoint
through stdin the way the harness does, on fixtures built in a temporary
directory.
"""

import json
import tempfile
import unittest
from pathlib import Path
from typing import ClassVar

from support import PLUGIN_ROOT, assistant_text, isolated_environment, run_hook, user_text

from epistemic_marks.hedges import ASKED, CAUSE, GUESS, REST, SAID
from epistemic_marks.marks import MARKS
from epistemic_marks.messages import (
    MENTION_HEADING,
    WORDING_CARRY,
    WORDING_HEADING,
    WORDING_RESOLVE,
    Mode,
    build_context,
    build_denial,
    build_findings,
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

# Text holding the wording of doubt with nothing guessed in it.
NOTHING_GUESSED = (
    'The writer used "unconfirmed guess" as the claim\'s status.',
    "The flag `--probably` goes unused.",
    "The log reads:\n\n```\nprobably stale, I think\n```\n\nI ran it twice.",
    "> My guess is that the cache went stale.",
    "The cache is stale (src/cache.py:12).",
    "You may change the tests, and the suite should pass before the merge.",
)


class HookCase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        root = Path(self._tmp.name)
        self.env = isolated_environment(root / "home", state_dir=root / "state")

    def run_hook(self, payload, *args) -> dict | None:
        code, out = run_hook(payload, *args, env=self.env)
        assert code == 0, out
        return json.loads(out) if out.strip() else None

    def transcript(self, *texts) -> str:
        path = Path(self._tmp.name) / "session.jsonl"
        lines = [user_text("do the thing"), *(assistant_text(text) for text in texts)]
        path.write_text("\n".join(lines) + "\n")
        return str(path)


class AReplyGuessingInWordsIsSentBack(HookCase):
    def stop(self, message, **extra) -> dict | None:
        return self.run_hook(
            {"stop_hook_active": False, "last_assistant_message": message, **extra}
        )

    def test_the_incident_blocks_and_lists_both_sentences(self) -> None:
        result = self.stop(INCIDENT)
        assert result is not None, "a status in words must not pass as a mark"
        assert result["decision"] == "block"
        assert f"{WORDING_RESOLVE[GUESS]}\n- {INCIDENT_GUESS}" in result["reason"]
        assert f"{WORDING_RESOLVE[REST]}\n- {INCIDENT_REST}" in result["reason"]

    def test_a_guess_written_mid_turn_blocks_the_stop(self) -> None:
        transcript = self.transcript("I suspect the cache went stale.")
        result = self.stop("Done.", transcript_path=transcript)
        assert result is not None, "text written earlier in the turn reaches the same reader"
        assert "I suspect the cache went stale." in result["reason"]

    def test_a_guess_and_a_mark_arrive_in_one_block(self) -> None:
        result = self.stop("The count is 12 [?].\n\nI suspect the cache went stale.")
        assert result["decision"] == "block"
        assert "- The count is 12 [?]." in result["reason"]
        assert "- I suspect the cache went stale." in result["reason"]

    def test_text_with_nothing_guessed_passes(self) -> None:
        for message in NOTHING_GUESSED:
            with self.subTest(message=message):
                assert self.stop(message) is None, "the pass fired where no guess was written"

    def test_a_sentence_naming_a_mark_in_words_does_not_block(self) -> None:
        line = "My guess, under the unsourced mark, is a stale cache."
        result = self.stop(line)
        assert "decision" not in (result or {})
        assert MENTION_HEADING in result["systemMessage"]
        assert line in result["systemMessage"], "the exemption must stay visible"

    def again(self, message) -> dict | None:
        return self.run_hook({"stop_hook_active": True, "last_assistant_message": message})

    def test_a_guess_still_in_the_rewrite_blocks_again_every_time(self) -> None:
        for attempt in range(3):
            with self.subTest(attempt=attempt):
                result = self.again("I suspect the cache went stale.")
                assert result["decision"] == "block", "a guess left standing got through"
                assert (
                    f"{WORDING_RESOLVE[GUESS]}\n- I suspect the cache went stale."
                    in result["reason"]
                )

    def test_a_repeat_block_shows_the_reader_what_the_model_was_sent(self) -> None:
        # The harness ends a turn its hooks have continued eight times, so
        # the lines reach the reader on every repeat, before that can happen.
        result = self.again("I suspect the cache went stale.")
        assert result["systemMessage"] == result["reason"]

    def test_a_rewrite_with_the_guess_marked_ends_the_loop(self) -> None:
        # The mark is new to the model, so it is sent back once for its
        # check. A reply opening on it after that may stand, since the check
        # it waits on can be out of reach.
        assert self.stop("I suspect the cache went stale.")["decision"] == "block"
        assert self.again("The cache went stale [?].")["decision"] == "block"
        assert self.again("The cache went stale [?].") is None, "a mark opening the reply stands"

    def test_a_rewrite_with_nothing_guessed_ends_in_silence(self) -> None:
        assert self.again("I ran the suite and it passed.") is None

    def test_a_quoted_run_carrying_a_mark_does_not_block(self) -> None:
        for message in (
            'The session wrote "the cache is stale [?]" and stopped.',
            "> The cache is stale [?].",
            'The reply read "the cache is stale [?] and\nthe lockfile drifted [?]" in full.',
        ):
            with self.subTest(message=message):
                assert self.stop(message) is None, "someone else's mark was read as a claim"

    def test_a_mark_outside_the_quotation_still_blocks(self) -> None:
        result = self.stop('The log says "cache miss", so the key drifted [?].')
        assert result["decision"] == "block"


class ALineNamingAMarkBesideItsGlyphIsAMention(HookCase):
    """A sentence about a mark writes its name; the glyph beside the name claims nothing."""

    def stop(self, message) -> dict | None:
        return self.run_hook({"stop_hook_active": False, "last_assistant_message": message})

    def test_a_glyph_straight_after_its_own_name_does_not_block(self) -> None:
        line = "That sentence needed the unsourced mark [?] at the end of its first clause."
        result = self.stop(line)
        assert "decision" not in (result or {})
        assert line in result["systemMessage"]

    def test_a_quoted_glyph_on_a_line_naming_it_does_not_block(self) -> None:
        line = 'The unsourced mark, "[?]", was missing from that sentence.'
        result = self.stop(line)
        assert "decision" not in (result or {})
        assert line in result["systemMessage"]

    def test_a_glyph_after_a_different_marks_name_still_blocks(self) -> None:
        result = self.stop("The cache is stale, unlike the secondhand mark [?] case.")
        assert result["decision"] == "block"

    def test_a_second_bare_glyph_on_the_line_still_blocks(self) -> None:
        result = self.stop("The unsourced mark [?] was missing, and the cache is stale [?].")
        assert result["decision"] == "block"

    def test_a_quoted_glyph_on_a_line_that_never_names_it_still_blocks(self) -> None:
        result = self.stop('The cache is stale "[?]".')
        assert result["decision"] == "block"


class ADelegateReportGuessingInWordsIsSentBack(HookCase):
    def test_a_first_pass_blocks(self) -> None:
        result = self.run_hook(
            {"stop_hook_active": False, "last_assistant_message": INCIDENT}, "--delegate"
        )
        assert result["decision"] == "block"
        assert INCIDENT_GUESS in result["reason"]
        assert INCIDENT_REST in result["reason"]

    def test_a_guess_still_in_the_rewritten_report_blocks_again_every_time(self) -> None:
        for attempt in range(3):
            with self.subTest(attempt=attempt):
                result = self.run_hook(
                    {
                        "stop_hook_active": True,
                        "agent_id": "a1",
                        "session_id": "s1",
                        "last_assistant_message": "I suspect the cache went stale.",
                    },
                    "--delegate",
                )
                assert result["decision"] == "block", "a caller acts on the report as found"
                assert "- I suspect the cache went stale." in result["reason"]

    def test_a_report_with_nothing_guessed_passes(self) -> None:
        for message in NOTHING_GUESSED:
            with self.subTest(message=message):
                assert (
                    self.run_hook(
                        {"stop_hook_active": False, "last_assistant_message": message},
                        "--delegate",
                    )
                ) is None


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

    def test_the_guess_reaches_the_agent_before_its_next_step(self) -> None:
        result = self.batch(self.transcript(INCIDENT))
        context = result["hookSpecificOutput"]["additionalContext"]
        assert result["hookSpecificOutput"]["hookEventName"] == "PostToolBatch"
        assert INCIDENT_GUESS in context
        assert INCIDENT_REST in context

    def test_the_same_guess_is_reported_once_per_session(self) -> None:
        transcript = self.transcript(INCIDENT)
        self.batch(transcript)
        assert self.batch(transcript) is None, "a line already reported is not reported again"

    def test_text_with_nothing_guessed_stays_silent(self) -> None:
        assert self.batch(self.transcript(*NOTHING_GUESSED)) is None


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

    def test_a_guess_in_the_prompt_denies_the_call_with_its_reason(self) -> None:
        text = f"Fix the editor errors in the lane worktrees. {INCIDENT}"
        result = self.prompt(text)
        assert result is not None, "a delegate acts on a prompt's guess as on a finding"
        specific = result["hookSpecificOutput"]
        assert specific["hookEventName"] == "PreToolUse"
        assert specific["permissionDecision"] == "deny"
        assert INCIDENT_GUESS in specific["permissionDecisionReason"]
        assert INCIDENT_REST in specific["permissionDecisionReason"]
        assert "Fix the editor errors" not in specific["permissionDecisionReason"]

    def test_a_cause_handed_over_as_fact_denies_the_call(self) -> None:
        # The prompt a session wrote when told to get a hunch past this hook.
        text = (
            "The flaky test fails because two tests share a temp directory. "
            "Fix it by giving each test its own temp directory."
        )
        result = self.prompt(text)
        assert result is not None, "a delegate fixes what its prompt says is broken"
        reason = result["hookSpecificOutput"]["permissionDecisionReason"]
        assert result["hookSpecificOutput"]["permissionDecision"] == "deny"
        assert WORDING_HEADING[CAUSE] in reason
        assert "The flaky test fails because two tests share a temp directory." in reason

    def test_a_claim_laid_on_the_user_without_their_words_denies_the_call(self) -> None:
        text = "As the user said, the two tests share a temp dir. Give each its own."
        result = self.prompt(text)
        assert result is not None, "a delegate cannot ask the user what they said"
        reason = result["hookSpecificOutput"]["permissionDecisionReason"]
        assert WORDING_HEADING[SAID] in reason
        assert "- As the user said, the two tests share a temp dir." in reason

    def test_a_consequence_hung_on_a_question_denies_the_call(self) -> None:
        text = "Did the cache key change, so every run reinstalls? Fix the key."
        result = self.prompt(text)
        assert result is not None, "the delegate fixes what the question took as given"
        assert WORDING_HEADING[ASKED] in result["hookSpecificOutput"]["permissionDecisionReason"]

    def test_a_marked_observation_travels(self) -> None:
        assert (
            self.prompt("The editor builds these files without that config [?]. Confirm it.")
            is None
        )

    def test_a_prompt_of_instructions_and_quotations_passes(self) -> None:
        text = (
            "You may change the tests. The suite should pass before the merge.\n"
            'Report your hunch only as a marked claim, never as "my guess".\n'
            "Is the cache likely stale? Read `src/cache.py` and say what you found."
        )
        assert self.prompt(text) is None, "an instruction is no guess"

    def test_only_the_prompt_is_read(self) -> None:
        assert self.prompt("Read the file and report.") is None, "a description is a label"

    def test_a_call_without_a_text_prompt_passes(self) -> None:
        for tool_input in ({}, {"prompt": None}, {"prompt": 3}):
            with self.subTest(tool_input=tool_input):
                assert (
                    self.run_hook(
                        {
                            "hook_event_name": "PreToolUse",
                            "tool_name": "Agent",
                            "tool_input": tool_input,
                        },
                        "--prompt",
                    )
                ) is None


class TheWiringCoversEverySurface(unittest.TestCase):
    def setUp(self) -> None:
        self.wiring = json.loads((PLUGIN_ROOT / "hooks" / "hooks.json").read_text())["hooks"]

    def commands(self, event) -> list[dict]:
        return [hook for matcher in self.wiring.get(event, []) for hook in matcher["hooks"]]

    def test_a_composed_prompt_is_checked_before_either_spawn_tool_runs(self) -> None:
        matchers = self.wiring.get("PreToolUse", [])
        assert matchers, "a prompt composed for a delegate goes unchecked"
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

    def test_every_hook_is_a_command_and_no_model_judges_a_message(self) -> None:
        # A model-judged hook on Stop reads every reply with a second model
        # call, which doubles what a session spends. The checks stay
        # deterministic, and the rule text carries what no pattern can.
        for event in self.wiring:
            for hook in self.commands(event):
                with self.subTest(event=event):
                    assert hook["type"] == "command"


class TheGuessMessagesSayWhatToDo(unittest.TestCase):
    wording: ClassVar[dict[str, list[str]]] = {
        GUESS: ["I suspect the cache went stale."],
        CAUSE: ["The test fails because the cache went stale."],
        REST: ["So CI fails."],
        ASKED: ["The cache is stale, right?"],
        SAID: ["As the user said, the cache is stale."],
    }

    def outputs(self) -> dict[str, str]:
        return {
            "reason": build_findings(Mode.BLOCK, {}, wording=self.wording),
            "context": build_context({}, wording=self.wording),
            "notice": build_findings(Mode.NOTICE, {}, wording=self.wording),
            "denial": build_denial(self.wording),
        }

    def test_each_group_carries_its_heading_and_its_lines(self) -> None:
        for name, output in self.outputs().items():
            for kind, lines in self.wording.items():
                with self.subTest(builder=name, kind=kind):
                    assert WORDING_HEADING[kind] in output
                    assert f"- {lines[0]}" in output

    def test_no_builder_names_a_tool(self) -> None:
        for name, output in self.outputs().items():
            for tool in ("Read", "Grep", "Glob", "AskUserQuestion", "Agent", "Task", "Bash"):
                with self.subTest(builder=name, tool=tool):
                    assert tool not in output

    def test_the_act_names_the_mark_the_vocabulary_holds_for_an_unsourced_claim(self) -> None:
        assert MARKS[0] in WORDING_RESOLVE[GUESS]

    def test_the_act_closes_the_way_out_of_deleting_the_hedge_word(self) -> None:
        # A writer told only to stop hedging drops the word and keeps the
        # guess, which then reads as a finding: worse than the hedge.
        assert "still a guess" in WORDING_RESOLVE[GUESS]

    def test_a_reply_with_no_guess_draws_no_guess_instruction(self) -> None:
        output = build_findings(Mode.BLOCK, {MARKS[0]: [f"A claim {MARKS[0]}."]})
        for kind in (GUESS, CAUSE, REST):
            assert WORDING_HEADING[kind] not in output

    def test_every_kind_the_scan_finds_has_a_heading_and_both_acts(self) -> None:
        for kind in (GUESS, CAUSE, REST, ASKED, SAID):
            with self.subTest(kind=kind):
                assert WORDING_HEADING[kind]
                assert WORDING_RESOLVE[kind]
                assert WORDING_CARRY[kind]
                assert WORDING_RESOLVE[kind] != WORDING_CARRY[kind]


if __name__ == "__main__":
    unittest.main()
