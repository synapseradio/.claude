"""Tests binding the enforced vocabulary to the rule text that teaches it.

    python3 -m unittest discover -s tests -p test_marks_vocabulary.py -v

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


def marks_taught_by(path: Path) -> set[str]:
    return set(MARK_SHAPED.findall(path.read_text()))


class TheVocabularyIsInternallyConsistent(unittest.TestCase):
    """Checks that need no rule body, so they always run."""

    def test_every_mark_carries_a_token_a_label_a_name_and_both_acts(self) -> None:
        for mark in VOCABULARY:
            assert mark.token, "a mark with no token cannot be found in a reply"
            assert mark.label, f"{mark.token} needs a label naming what it asks for"
            assert mark.name, f"{mark.token} needs a name a sentence can use"
            assert mark.resolve, f"{mark.token} needs the act to take when it can be settled here"
            assert mark.carry, f"{mark.token} needs the act to take when it travels in the report"

    def test_no_two_marks_share_a_token(self) -> None:
        tokens = [mark.token for mark in VOCABULARY]
        assert len(tokens) == len(set(tokens)), "a duplicated token makes a mark ambiguous"

    def test_every_token_is_mark_shaped(self) -> None:
        for token in MARKS:
            assert re.search(MARK_SHAPED, token), (
                f"{token} does not match the shape the conformance test scans for, "
                "so a rule body teaching it would read as an extra mark"
            )

    def test_the_derived_lookups_cover_exactly_the_vocabulary(self) -> None:
        assert set(MARK_NAMES) == set(MARKS)
        assert set(MARK_RESOLVE) == set(MARKS)
        assert set(MARK_CARRY) == set(MARKS)

    def test_every_relaying_mark_rides_up_from_a_delegate(self) -> None:
        # run_stop pops exactly RELAY_MARKS out of a delegate's blocking set,
        # so a relaying label missing from that tuple would block the delegate
        # on a question the delegate cannot reach.
        relaying = tuple(mark.token for mark in VOCABULARY if mark.label in RELAYING)
        assert relaying == RELAY_MARKS, (
            "a relaying token missing from RELAY_MARKS strands a delegate on a question only someone above it can answer"
        )

    def test_the_two_relaying_labels_hold_different_tokens(self) -> None:
        escalating = {m.token for m in VOCABULARY if m.label == ESCALATE_DECISION}
        asking = {m.token for m in VOCABULARY if m.label == ASK_USER}
        assert escalating, "the caller's mark is what rides one level up"
        assert asking, "the standing question is what reaches a person"
        assert not escalating & asking, (
            "one token under both labels leaves a caller unable to tell an item it could settle itself from one that must reach a person"
        )

    def test_at_least_one_label_sits_outside_the_relaying_set(self) -> None:
        assert [mark for mark in VOCABULARY if mark.label not in RELAYING], (
            "with every mark relaying, a delegate would hand up everything and the hook would never ask anyone for a citation"
        )

    def test_every_mark_carries_a_declared_label(self) -> None:
        # A label carries behavior, so adding one means placing it inside
        # RELAYING or outside on purpose. A label nobody declared reads as
        # non-relaying by default, silently, and the delegate blocks.
        declared = {NEEDS_CITATION, NEEDS_VERIFICATION, ESCALATE_DECISION, ASK_USER}
        for mark in VOCABULARY:
            with self.subTest(mark=mark.token):
                assert mark.label in declared, (
                    f"{mark.token} carries a label nobody declared, so nobody decided "
                    "whether a delegate settles it here or hands it up"
                )

    def test_the_relaying_set_names_only_labels_a_mark_carries(self) -> None:
        carried = {mark.label for mark in VOCABULARY}
        assert not RELAYING - carried, (
            f"RELAYING names {sorted(RELAYING - carried)}, which no mark carries, "
            "so a token was renamed or removed and the set did not follow"
        )

    def test_no_two_marks_share_an_act(self) -> None:
        for field in ("resolve", "carry"):
            acts = [getattr(mark, field) for mark in VOCABULARY]
            with self.subTest(act=field):
                assert len(acts) == len(set(acts)), (
                    f"two marks give the same {field} instruction, so one was copied "
                    "in without being given an act of its own"
                )


class TheShippedRuleTextMatchesWhatIsEnforced(unittest.TestCase):
    """Both artifacts ship here, so a mismatch is this plugin's own defect."""

    def test_it_teaches_every_mark_the_hooks_block(self) -> None:
        missing = set(MARKS) - marks_taught_by(SHIPPED_RULE_BODY)
        assert not missing, (
            f"the shipped rule text teaches no {sorted(missing)}, so the hooks block a "
            "mark this plugin never taught a model to write or clear"
        )

    def test_it_teaches_no_mark_the_hooks_ignore(self) -> None:
        extra = marks_taught_by(SHIPPED_RULE_BODY) - set(MARKS)
        assert not extra, (
            f"the shipped rule text teaches {sorted(extra)}, which the hooks never "
            "check, so a claim under it leaves the session unverified in silence"
        )


if __name__ == "__main__":
    unittest.main()
