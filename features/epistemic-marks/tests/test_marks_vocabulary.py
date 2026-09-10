"""Tests binding the enforced vocabulary to the rule text that teaches it.

    python3.14 -m pytest tests/test_marks_vocabulary.py -v

Both sides ship here, so a disagreement between them is this plugin's own
defect and needs nothing from outside to detect.
"""

import re
import sys
import unittest
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PLUGIN_ROOT))

from epistemic_marks.marks import (  # noqa: E402
    ASK,
    ASK_MARK,
    EVIDENCE,
    MARK_MEANINGS,
    MARK_NAMES,
    MARKS,
    VOCABULARY,
    tokens_of_class,
)

SHIPPED_RULE_BODY = PLUGIN_ROOT / "rule-text" / "epistemic-marks.md"

# The pattern is wider than the vocabulary, so text teaching a mark this
# plugin never checks shows up as an extra rather than passing unseen.
MARK_SHAPED = re.compile(r"\[[^\]\w\s]{0,3}\?\]")


def marks_taught_by(path):
    return set(MARK_SHAPED.findall(path.read_text()))


class TheVocabularyIsInternallyConsistent(unittest.TestCase):
    """Checks that need no rule body, so they always run."""

    def test_every_mark_carries_a_token_a_name_a_gloss_and_a_resolution(self):
        for mark in VOCABULARY:
            self.assertTrue(mark.token, "a mark with no token cannot be found in a reply")
            self.assertTrue(mark.name, f"{mark.token} needs a name a sentence can use")
            self.assertTrue(mark.gloss, f"{mark.token} needs a gloss the block message shows")
            self.assertIn(
                mark.resolution,
                (EVIDENCE, ASK),
                f"{mark.token} must resolve either through evidence or through the user",
            )

    def test_no_two_marks_share_a_token(self):
        tokens = [mark.token for mark in VOCABULARY]
        self.assertEqual(len(tokens), len(set(tokens)), "a duplicated token makes a mark ambiguous")

    def test_every_token_is_mark_shaped(self):
        for token in MARKS:
            self.assertRegex(
                token,
                MARK_SHAPED,
                f"{token} does not match the shape the conformance test scans for, "
                "so a rule body teaching it would read as an extra mark",
            )

    def test_the_derived_lookups_cover_exactly_the_vocabulary(self):
        self.assertEqual(set(MARK_MEANINGS), set(MARKS))
        self.assertEqual(set(MARK_NAMES), set(MARKS))

    def test_exactly_one_mark_resolves_through_the_user(self):
        self.assertEqual(
            tokens_of_class(ASK),
            (ASK_MARK,),
            "run_stop carries one ASK token upward; a second would be dropped silently",
        )

    def test_at_least_one_mark_resolves_through_evidence(self):
        self.assertTrue(
            tokens_of_class(EVIDENCE),
            "with no evidence mark the hook would never ask for a citation",
        )


class TheShippedRuleTextMatchesWhatIsEnforced(unittest.TestCase):
    """Both artifacts ship here, so a mismatch is this plugin's own defect."""

    def test_it_teaches_every_mark_the_hooks_block(self):
        missing = set(MARKS) - marks_taught_by(SHIPPED_RULE_BODY)
        self.assertFalse(
            missing,
            f"the shipped rule text teaches no {sorted(missing)}, so the hooks block a "
            "mark this plugin never taught a model to write or clear",
        )

    def test_it_teaches_no_mark_the_hooks_ignore(self):
        extra = marks_taught_by(SHIPPED_RULE_BODY) - set(MARKS)
        self.assertFalse(
            extra,
            f"the shipped rule text teaches {sorted(extra)}, which the hooks never "
            "check, so a claim under it leaves the session unverified in silence",
        )

    def test_it_gives_each_mark_the_name_the_messages_use(self):
        body = SHIPPED_RULE_BODY.read_text().lower()
        for token, name in MARK_NAMES.items():
            bare = name.removeprefix("the ").removesuffix(" mark")
            self.assertIn(
                bare,
                body,
                f"the messages call {token} {name!r}, and the shipped rule text never "
                f"uses {bare!r}, so a writer told to name the mark in words has none",
            )

    def test_it_scopes_the_no_mark_exception_to_this_conversation(self):
        # The rule corpus this plugin's text is reconciled against (see
        # rulesets/default/epistemic-marks.md) draws a real line here: the
        # user's own statements in live conversation need no mark, but the
        # user's own comment attached to a change still counts as secondhand
        # and needs [.?], since a note written earlier can go stale. Drop the
        # "in this conversation" qualifier and the exception reads wide enough
        # to swallow that comment, so both halves are pinned here.
        body = SHIPPED_RULE_BODY.read_text()
        self.assertIn(
            "The user's statements in this conversation",
            body,
            "the shipped text must scope its no-mark exception to live conversation, "
            "or a stale comment the user wrote earlier reads as needing no mark",
        )
        self.assertIn(
            "Count the user's comment on a change as secondhand",
            body,
            "the exception's other half: without it the scoping above has nothing "
            "to exclude, and the pin passes on a text that lost the distinction",
        )


if __name__ == "__main__":
    unittest.main()
