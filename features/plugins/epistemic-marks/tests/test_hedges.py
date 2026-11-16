"""Tests for the scan that finds a guess written in words where a mark belongs.

    python3 -m unittest discover -s tests -p test_hedges.py -v

Two sides are held here, and the second matters as much as the first. A scan
that misses a guess lets it reach a reader as a finding. A scan that fires on
a quotation, on code, or on an instruction teaches the writer to ignore it.
"""

import unittest

from epistemic_marks.hedges import ASKED, CAUSE, GUESS, REST, SAID, guessed_lines

# The message that prompted the check: a status in words, then a sentence
# building on it. A later diagnosis ruled the claim out.
INCIDENT_GUESS = (
    "My unconfirmed guess is that files in the lane worktrees fall into a project "
    "the editor builds without that config."
)
INCIDENT_REST = (
    "That would leave them without the claude-code path, Node types or JSX settings, "
    "which matches the errors."
)

GUESSES = (
    INCIDENT_GUESS,
    "My guess is the cache went stale.",
    "Best guess: the cache went stale.",
    "I'm guessing the cache went stale.",
    "I suspect the cache went stale.",
    "I think the watcher holds the file open.",
    "I believe the watcher holds the file open.",
    "I'd say the watcher holds the file open.",
    "We assume the watcher holds the file open.",
    "The cache is probably stale.",
    "It is likely the cache.",
    "The likely cause is the cache.",
    "Plausibly the lockfile drifted.",
    "Presumably the watcher holds the file open.",
    "Perhaps the lockfile drifted.",
    "Maybe the lockfile drifted.",
    "The lockfile may have drifted.",
    "It may well be the lockfile.",
    "The failure may be due to the lockfile.",
    "The new flag should resolve it.",
    "A stale cache is a plausible cause.",
    "That reading is plausible.",
    "It appears the watcher holds the file open.",
    "The watcher might hold the file open.",
    "It seems the watcher holds the file open.",
    "The watcher appears to hold the file open.",
    "Looks like the watcher holds the file open.",
    "That should fix it.",
    "The patch should be enough.",
    "The cause should be the stale cache.",
    "Hypothesis: the watcher holds the file open.",
    "The working theory is a stale cache.",
    "Unconfirmed: the watcher holds the file open.",
    "The diagnosis is still unverified.",
    "I haven't checked this, but the watcher holds the file open.",
    "The watcher holds the file open, though I haven't verified it.",
    "The watcher holds the file open (unverified).",
    "The watcher holds the file open (?).",
    "The watcher holds the file open [unverified].",
    "As far as I can tell the watcher holds the file open.",
    "If I recall correctly, the flag landed in version 3.",
    "My understanding is that the hook runs twice.",
    "I'm fairly confident the hook runs twice.",
    "The hook almost certainly runs twice.",
    "Chances are the hook runs twice.",
    "It could be that the hook runs twice.",
    "- **Cause:** probably the stale cache.",
    # A source with its name filed off.
    "Some say the watcher holds the file open.",
    "Many believe the flag landed in version 3.",
    "It is said that the hook runs twice.",
    "It is widely known that the hook runs twice.",
    "Rumor has it the hook runs twice.",
    # A status summary in words, standing over claims in place of their marks.
    "I haven't read any code, so all three are guesses.",
    "Everything below is a guess from common patterns.",
    "These are assumptions until someone reads the test.",
    "The rest is speculation on my part.",
    # A noun that labels the claim, where it opens its clause.
    "The theory is that the cache went stale.",
    "One hypothesis is a stale cache.",
    "The cache looks fine, but the theory is that it went stale.",
    # A modal in a frame where only the doubting sense fits.
    "It may be the lockfile.",
    "It could be the lockfile.",
    "That may be the stale cache again.",
    "The tests should pass now.",
    "The build should now succeed.",
)

QUIET = (
    # A mark or a source already does the job the wording was standing in for.
    "The cache is probably stale [?].",
    "The delegate says the cache is likely stale [.?].",
    "The docs say the value may be null (https://example.com/api#value).",
    "It probably fails at `src/a.py:12`.",
    # Someone else's words, and words about words.
    'The writer used "unconfirmed guess" as the claim\'s status.',
    "The writer used “my guess” as the claim\u2019s status.",
    "Replace 'I believe' with the mark.",
    # The request named the guess; the sentence only repeats what was asked.
    "You asked for a hunch without reading code, so I left these unchecked.",
    "> My guess is that the cache went stale.",
    # Code.
    "The flag `--probably` goes unused.",
    "Run `git log --grep='I think'` to find them.",
    # A question asserts nothing.
    "Is the cache probably stale?",
    # Permission, obligation and appearance share words with doubt.
    "You may change the tests and the README.",
    "The agent may edit the README.",
    "The function should return a list.",
    "You should run the suite first.",
    "The banner appears after login.",
    "The output looks like this:",
    "For what a valid change looks like, read the reference.",
    "None of it appears until the pipe closes.",
    "A variant file may be empty.",
    "The artifact may be code, tests, config or docs.",
    "State the action under each plausible answer.",
    "The designer settles how something that runs should work.",
    "You should fix the lint errors before the merge.",
    "See [guess](#guess) for the section on it.",
    "You might want to read DESIGN.md first.",
    # Talk about guessing, in someone else's mouth or in general.
    "Report your hunch about the flaky test.",
    "Voice a hypothesis as a hypothesis and test it.",
    "Stop guessing and read the file.",
    "Some tests say more than others.",
    "The docs say the hook runs twice (docs/hooks.md:12).",
    # The first-person account the rule asks for when a claim is dropped.
    "I didn't check these, because none of them reach the page.",
    # A plain report of what happened.
    "The suite passed: 107 tests.",
    "I ran the suite and it passed.",
    # A sentence about guesses, where the noun labels no claim of the writer's.
    "A prompt carrying a guess is denied before the delegate starts.",
    "A reply that states a theory is sent back.",
    "Each hypothesis was tested in turn.",
    "The sentence carries no doubt wording and no formatting tricks.",
    # What a format allows and what a contract obliges.
    "It may be a string or a number.",
    "It must be the first argument.",
    "The tests should pass before the merge.",
    "The job should run again after the cache clears.",
    # An open question, and a question about what to do.
    "Is the cache stale?",
    "Did you run the tests?",
    "Should I run the suite, so we know?",
    "You want JSON output, right?",
    "Don't you want the suite run first?",
    # The user's words, quoted, and talk about users in general.
    'The user said "the two tests share a temp dir".',
    "When the user says yes, the form submits.",
    "Ask the user whether the cache is stale.",
    "The user asked for JSON output.",
    "The user said to skip the e2e suite.",
    "The work rests on what the user said they want.",
    "The answer would contradict what the user stated.",
    "Leave it unmarked where the user stated it in this conversation.",
)


def found(text) -> dict[str, list[str]]:
    wording, _mentions = guessed_lines([text])
    return wording


class AGuessInWordsIsFound(unittest.TestCase):
    def test_each_guess_is_flagged(self) -> None:
        for line in GUESSES:
            with self.subTest(line=line):
                assert found(line).get(GUESS) == [line], (
                    "wording stood in for the mark and the scan let it through"
                )

    def test_the_guess_is_reported_as_the_sentence_that_carries_it(self) -> None:
        text = "The suite passed. I suspect the cache went stale. I ran it twice."
        assert found(text) == {GUESS: ["I suspect the cache went stale."]}

    def test_a_guess_is_reported_once(self) -> None:
        text = "I suspect the cache went stale.\n\nI suspect the cache went stale."
        assert found(text) == {GUESS: ["I suspect the cache went stale."]}


class TheScanStaysQuietWhereNothingIsGuessed(unittest.TestCase):
    def test_each_quiet_line_passes(self) -> None:
        for line in QUIET:
            with self.subTest(line=line):
                assert found(line) == {}, "the scan fired where no guess was written"

    def test_a_fenced_block_is_code(self) -> None:
        text = "The log reads:\n\n```\nprobably stale, I think\n```\n\nI ran it twice."
        assert found(text) == {}

    def test_a_quotation_spanning_sentences_stays_quoted(self) -> None:
        text = 'The message read "My guess is the cache. That would explain it." and no more.'
        assert found(text) == {}


class WhatTheFloorLeavesToTheRuleText(unittest.TestCase):
    """The boundary, pinned so that moving it is a decision.

    Each sentence guesses, and nothing visible on it says so. A modal reads
    the same to a parser whether it doubts or obliges, and a guess stated
    flat carries no wording at all. The rule text sorts these by where the
    claim's support sits, which only the writer knows.
    """

    def test_a_guess_no_wording_gives_away_passes_the_scan(self) -> None:
        for line in (
            "It must be the cache.",
            "The file may be empty.",
            # A prompt handing over a diagnosis with no wording of doubt.
            "Fix the shared temp-dir collision between the two tests.",
            "Since the tests share a temp dir, give each test its own.",
            "Two tests share a temp directory. The flaky test fails.",
            'Ticket: "The flaky test fails because two tests share a temp directory." Fix it.',
            "The parser could be the slow part.",
            "Files in the lane worktrees fall into a project the editor builds without that config.",
            "Did a lockfile change land this week and alter the cache key?",
        ):
            with self.subTest(line=line):
                assert found(line) == {}


class ACauseStatedFlatIsFound(unittest.TestCase):
    """A diagnosis is the one flat guess with a visible form.

    The rule asks a source beside a cause the writer saw and a mark on one
    they reasoned to, so a sentence stating why something fails with neither
    is unfinished either way. Both escapes below came from sessions told to
    get a guess past the hooks.
    """

    def test_each_uncited_diagnosis_is_flagged(self) -> None:
        for line in (
            "Your CI build got slower this week because the dependency cache is being missed.",
            "The flaky test fails because two tests share a temp directory.",
            "The root cause is a cache key that stopped matching.",
            "The timeout was caused by a leaked file handle.",
            "The reason is that the watcher holds the file open.",
        ):
            with self.subTest(line=line):
                assert found(line) == {CAUSE: [line]}

    def test_a_diagnosis_with_its_source_or_its_mark_passes(self) -> None:
        for line in (
            "The test fails because the fixture path is wrong (tests/conftest.py:14).",
            "The test fails because two tests share a temp directory [?].",
        ):
            with self.subTest(line=line):
                assert found(line) == {}

    def test_a_reason_for_an_act_or_an_instruction_is_no_diagnosis(self) -> None:
        for line in (
            "I skipped the e2e suite because it needs credentials.",
            "Keep the summary short because the reader is busy.",
            "Find out why the build fails.",
            "Does the build fail because the cache is stale?",
            'The log says "failed because the cache is stale".',
        ):
            with self.subTest(line=line):
                assert found(line) == {}

    def test_a_sentence_building_on_a_flat_cause_is_found(self) -> None:
        cause = "The test fails because two tests share a temp directory."
        assert found(f"{cause} That would explain the order dependence.") == {
            CAUSE: [cause],
            REST: ["That would explain the order dependence."],
        }


class ASentenceRestingOnAGuessIsFound(unittest.TestCase):
    def test_the_incident_yields_both_sentences(self) -> None:
        assert found(f"{INCIDENT_GUESS} {INCIDENT_REST}") == {
            GUESS: [INCIDENT_GUESS],
            REST: [INCIDENT_REST],
        }

    def test_a_sentence_building_on_a_marked_claim_needs_the_mark_too(self) -> None:
        for rest in (
            "That would explain the failing install.",
            "So the install fails on CI.",
            "Which matches the log.",
            "Therefore the install fails on CI.",
            "This means the install fails on CI.",
            "If so, the install fails on CI.",
        ):
            with self.subTest(rest=rest):
                assert found(f"The lockfile drifted [?]. {rest}") == {REST: [rest]}, (
                    "the mark must travel into the line resting on the claim"
                )

    def test_the_chain_carries_through_each_resting_sentence(self) -> None:
        text = "The lockfile drifted [?]. That would break the install. So CI fails."
        assert found(text) == {REST: ["That would break the install.", "So CI fails."]}

    def test_a_resting_sentence_on_the_next_list_line_is_found(self) -> None:
        text = "- The lockfile drifted [?].\n- That would break the install."
        assert found(text) == {REST: ["- That would break the install."]}

    def test_a_resting_sentence_with_its_own_mark_passes(self) -> None:
        assert found("The lockfile drifted [?]. That would break the install [?].") == {}

    def test_a_resting_sentence_with_its_own_source_passes(self) -> None:
        assert found("The lockfile drifted [?]. So the install fails (ci/log.txt:41).") == {}

    def test_a_connective_after_a_sourced_claim_passes(self) -> None:
        assert found("The suite passed (log.txt:3). So the branch is ready.") == {}

    def test_a_connective_after_a_plain_report_passes(self) -> None:
        assert found("I ran the suite. That would have caught a regression.") == {}

    def test_a_next_step_after_a_marked_claim_passes(self) -> None:
        assert found("The lockfile drifted [?]. So I'll read it next.") == {}

    def test_a_blank_line_ends_the_reach_of_a_claim(self) -> None:
        assert found("The lockfile drifted [?].\n\nSo the suite is green.") == {}


class ASentenceNamingAMarkInWordsIsAMention(unittest.TestCase):
    def test_it_is_not_flagged_as_a_guess(self) -> None:
        line = "The unsourced mark replaces a phrase such as my guess."
        assert found(line) == {}

    def test_it_is_handed_back_as_a_mention_so_the_exemption_stays_visible(self) -> None:
        line = "My guess, under the unsourced mark, is a stale cache."
        _wording, mentions = guessed_lines([line])
        assert mentions == {"[?]": [line]}

    def test_a_sentence_naming_a_mark_with_nothing_guessed_is_no_mention(self) -> None:
        _wording, mentions = guessed_lines(["The unsourced mark sits at the end of a clause."])
        assert mentions == {}


class AClaimCarriedInAQuestionIsFound(unittest.TestCase):
    """A question that asserts, by its form, what it seems to ask.

    An open question hands a hypothesis over for checking and stays quiet.
    These forms do more: one hangs a consequence on its own premise, one
    states the claim and asks only for agreement, one leads with a negative.
    """

    def test_each_asserting_question_is_flagged(self) -> None:
        for line in (
            "Did a lockfile change land this week and alter the cache key, so every run reinstalls?",
            "Is the cache key stale, which would explain the reinstalls?",
            "The cache is stale, right?",
            "The cache went stale, didn't it?",
            "Isn't the cache stale?",
            "Doesn't the watcher hold the file open?",
        ):
            with self.subTest(line=line):
                assert found(line) == {ASKED: [line]}

    def test_a_marked_or_sourced_question_passes(self) -> None:
        for line in (
            "The cache is stale [?], right?",
            "Isn't the cache stale (src/cache.py:12)?",
        ):
            with self.subTest(line=line):
                assert found(line) == {}

    def test_a_sentence_building_on_a_question_is_found(self) -> None:
        assert found("Is the cache stale? That would explain the reinstalls.") == {
            REST: ["That would explain the reinstalls."]
        }

    def test_a_next_step_or_a_status_after_a_question_passes(self) -> None:
        for text in (
            "Is the cache stale? So I'll read the key next.",
            "Did the suite pass? So far, yes (log.txt:3).",
            "Want me to run it? That would take one call.",
        ):
            with self.subTest(text=text):
                assert found(text) == {}


class AClaimLaidOnTheUserIsFound(unittest.TestCase):
    """The user's statement goes unmarked only in words a reader can find.

    A sentence that reports what the user said, without quoting it, borrows
    the one unmarked status the rule grants and shows nothing to check.
    """

    def test_each_unquoted_attribution_is_flagged(self) -> None:
        for line in (
            "As the user said, the two tests share a temp dir.",
            "The user confirmed that the cache is stale.",
            "According to the user, the cache is stale.",
            "Per the user, both tests share a directory.",
            "The user has already stated the lockfile drifted.",
        ):
            with self.subTest(line=line):
                assert found(line) == {SAID: [line]}

    def test_a_quoted_marked_or_sourced_attribution_passes(self) -> None:
        for line in (
            'As the user said, "the two tests share a temp dir".',
            "As the user said, the two tests share a temp dir [.?].",
            "The user confirmed that the cache is stale (notes/call.md:4).",
        ):
            with self.subTest(line=line):
                assert found(line) == {}

    def test_a_sentence_building_on_an_attribution_is_found(self) -> None:
        said = "According to the user, the cache is stale."
        assert found(f"{said} So the install reruns.") == {
            SAID: [said],
            REST: ["So the install reruns."],
        }


class AQuotationWrappedAcrossLinesStaysQuoted(unittest.TestCase):
    def test_a_quotation_broken_by_a_line_end_holds_no_guess(self) -> None:
        text = 'The message read "My guess is the cache.\nThat would explain it." and no more.'
        assert found(text) == {}

    def test_a_guess_after_the_wrapped_quotation_is_still_found(self) -> None:
        text = 'The message read "the cache\nis stale" and I suspect it is right.'
        assert found(text) == {GUESS: ['is stale" and I suspect it is right.']}

    def test_a_wrapped_line_opens_no_sentence_of_its_own(self) -> None:
        for text in (
            "The second pass leaves it\nunchecked, for the reason the next section gives.",
            "The lockfile drifted [?] and\nSo-called fixes did not help (log.txt:2), which\nthat would explain.",
        ):
            with self.subTest(text=text):
                assert found(text) == {}

    def test_a_list_item_opens_a_sentence_whatever_the_item_above_ends_on(self) -> None:
        text = "- I suspect the lockfile drifted\n- That would break the install"
        assert found(text) == {
            GUESS: ["- I suspect the lockfile drifted"],
            REST: ["- That would break the install"],
        }

    def test_a_line_after_a_finished_sentence_still_opens_one(self) -> None:
        text = "The second pass ran.\nUnchecked: the watcher holds the file open."
        assert found(text) == {GUESS: ["Unchecked: the watcher holds the file open."]}

    def test_a_quotation_does_not_reach_across_a_blank_line(self) -> None:
        text = (
            'The message opened with a stray " mark.\n\nI suspect the cache went stale, "probably".'
        )
        assert found(text) == {GUESS: ['I suspect the cache went stale, "probably".']}


if __name__ == "__main__":
    unittest.main()
