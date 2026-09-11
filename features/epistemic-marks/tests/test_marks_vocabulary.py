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
    ASK_USER,
    ESCALATE_DECISION,
    MARK_CARRY,
    MARK_NAMES,
    MARK_RESOLVE,
    MARKS,
    NEEDS_CITATION,
    NEEDS_VERIFICATION,
    RELAY_MARKS,
    RELAYING,
    VOCABULARY,
)

SHIPPED_RULE_BODY = PLUGIN_ROOT / "rule-text" / "epistemic-marks.md"

# The pattern is wider than the vocabulary, so text teaching a mark this
# plugin never checks shows up as an extra rather than passing unseen.
MARK_SHAPED = re.compile(r"\[[^\]\w\s]{0,3}\?\]")


def marks_taught_by(path):
    return set(MARK_SHAPED.findall(path.read_text()))


class TheVocabularyIsInternallyConsistent(unittest.TestCase):
    """Checks that need no rule body, so they always run."""

    def test_every_mark_carries_a_token_a_label_a_name_and_both_acts(self):
        for mark in VOCABULARY:
            self.assertTrue(mark.token, "a mark with no token cannot be found in a reply")
            self.assertTrue(mark.label, f"{mark.token} needs a label naming what it asks for")
            self.assertTrue(mark.name, f"{mark.token} needs a name a sentence can use")
            self.assertTrue(
                mark.resolve, f"{mark.token} needs the act to take when it can be settled here"
            )
            self.assertTrue(
                mark.carry, f"{mark.token} needs the act to take when it travels in the report"
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
        self.assertEqual(set(MARK_NAMES), set(MARKS))
        self.assertEqual(set(MARK_RESOLVE), set(MARKS))
        self.assertEqual(set(MARK_CARRY), set(MARKS))

    def test_every_relaying_mark_rides_up_from_a_delegate(self):
        # run_stop pops exactly RELAY_MARKS out of a delegate's blocking set,
        # so a relaying label missing from that tuple would block the delegate
        # on a question the delegate cannot reach.
        relaying = tuple(mark.token for mark in VOCABULARY if mark.label in RELAYING)
        self.assertEqual(
            relaying,
            RELAY_MARKS,
            "a relaying token missing from RELAY_MARKS strands a delegate "
            "on a question only someone above it can answer",
        )

    def test_the_two_relaying_labels_hold_different_tokens(self):
        escalating = {m.token for m in VOCABULARY if m.label == ESCALATE_DECISION}
        asking = {m.token for m in VOCABULARY if m.label == ASK_USER}
        self.assertTrue(escalating, "the caller's mark is what rides one level up")
        self.assertTrue(asking, "the standing question is what reaches a person")
        self.assertFalse(
            escalating & asking,
            "one token under both labels leaves a caller unable to tell an item it "
            "could settle itself from one that must reach a person",
        )

    def test_at_least_one_label_sits_outside_the_relaying_set(self):
        self.assertTrue(
            [mark for mark in VOCABULARY if mark.label not in RELAYING],
            "with every mark relaying, a delegate would hand up everything and "
            "the hook would never ask anyone for a citation",
        )

    def test_every_mark_carries_a_declared_label(self):
        # A label carries behavior, so adding one means placing it inside
        # RELAYING or outside on purpose. A label nobody declared reads as
        # non-relaying by default, silently, and the delegate blocks.
        declared = {NEEDS_CITATION, NEEDS_VERIFICATION, ESCALATE_DECISION, ASK_USER}
        for mark in VOCABULARY:
            with self.subTest(mark=mark.token):
                self.assertIn(
                    mark.label,
                    declared,
                    f"{mark.token} carries a label nobody declared, so nobody decided "
                    "whether a delegate settles it here or hands it up",
                )

    def test_the_relaying_set_names_only_labels_a_mark_carries(self):
        carried = {mark.label for mark in VOCABULARY}
        self.assertFalse(
            RELAYING - carried,
            f"RELAYING names {sorted(RELAYING - carried)}, which no mark carries, "
            "so a token was renamed or removed and the set did not follow",
        )

    def test_no_two_marks_share_an_act(self):
        for field in ("resolve", "carry"):
            acts = [getattr(mark, field) for mark in VOCABULARY]
            with self.subTest(act=field):
                self.assertEqual(
                    len(acts),
                    len(set(acts)),
                    f"two marks give the same {field} instruction, so one was copied "
                    "in without being given an act of its own",
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

    def test_it_gives_each_mark_the_name_a_mention_has_to_use(self):
        body = SHIPPED_RULE_BODY.read_text().lower()
        for token, name in MARK_NAMES.items():
            bare = name.removeprefix("the ").removesuffix(" mark")
            self.assertIn(
                bare,
                body,
                f"scan.py exempts a line only where it calls {token} {name!r}, and the "
                f"shipped rule text never uses {bare!r}, so a writer told to name the "
                "mark in words rather than write the glyph has no name to reach for",
            )

    def test_it_scopes_the_no_mark_exception_to_this_conversation(self):
        # This plugin's text is the rule's one home, and it draws a real line here: the
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
