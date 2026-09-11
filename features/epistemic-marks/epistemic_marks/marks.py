"""The epistemic-mark vocabulary these hooks enforce.

Every other module reads the vocabulary from here and writes no mark token as
a literal. tests/test_marks_vocabulary.py compares it against the rule text
that teaches it.

A mark's meaning lives in that rule text and nowhere here. What lives here is
what to do about a mark, which is the plugin's half of the pair.
"""

from dataclasses import dataclass

# A label names what the mark asks for. It is the class: nothing groups the
# marks above this, since each one carries its own two acts.
NEEDS_CITATION = "needs_citation"
NEEDS_VERIFICATION = "needs_verification"
ESCALATE_DECISION = "escalate_decision"
ASK_USER = "ask_user"

# The labels whose answer sits outside the agent that wrote the mark, so a
# delegate's Stop pass leaves them for the report rather than blocking on
# them. A label placed in neither this set nor outside it strands a delegate,
# and tests/test_marks_vocabulary.py fails on one.
RELAYING = frozenset({ESCALATE_DECISION, ASK_USER})


@dataclass(frozen=True)
class Mark:
    """A mark, its label, and the two acts that close it.

    `resolve` is the act when the mark can be settled in this pass. `carry` is
    the act when it cannot and the mark travels in the report instead. Every
    mark has both, since an unsourced claim left unground rides up exactly as
    an escalation does. No instruction names a tool, because the agent reading
    it runs on a machine whose toolset this plugin cannot know.
    """

    token: str
    label: str
    name: str
    resolve: str
    carry: str


VOCABULARY = (
    Mark(
        token="[?]",
        label=NEEDS_CITATION,
        name="the unsourced mark",
        resolve=(
            "Gather the evidence for each claim below. Replace the mark in place "
            "with the source you reached, a path or a URL. Narrow any statements the "
            "evidence narrows, and remove one it contradicts."
        ),
        carry=(
            "Leave each claim below marked and open your report on it, beside the "
            "evidence it waits on and the lookup already tried."
        ),
    ),
    Mark(
        token="[.?]",
        label=NEEDS_VERIFICATION,
        name="the secondhand mark",
        resolve=(
            "Verify each relayed claim below against its own source. Replace the "
            "mark in place with that source. Narrow or remove any statements the "
            "source does not back."
        ),
        carry=(
            "Leave each claim below marked and open your report on it, beside the "
            "source that would settle it."
        ),
    ),
    Mark(
        token="[^?]",
        label=ESCALATE_DECISION,
        name="the caller's mark",
        resolve=(
            "Put the question each line below stands on to your caller, with the "
            "options you would offer, and let the answer replace the mark."
        ),
        carry=(
            "Leave each line below exactly where it stands. Open your report on the "
            "question it carries, with the options you would have offered."
        ),
    ),
    Mark(
        token="[!?]",
        label=ASK_USER,
        name="the standing question",
        resolve=(
            "Put the question each line below stands on to a person, with the "
            "options you would offer, and let the answer replace the mark."
        ),
        carry=(
            "Leave each line below exactly where it stands. Open your report on the "
            "question it carries, with situational context for clarity. Say "
            "that the decision must be made by the user"
        ),
    ),
)

MARKS = tuple(mark.token for mark in VOCABULARY)

MARK_NAMES = {mark.token: mark.name for mark in VOCABULARY}

MARK_RESOLVE = {mark.token: mark.resolve for mark in VOCABULARY}

MARK_CARRY = {mark.token: mark.carry for mark in VOCABULARY}

# Every token a delegate leaves for its report instead of resolving itself. A
# single token would drop the second one silently, which is what the split of
# the escalation mark into a caller's mark and a standing question introduced.
RELAY_MARKS = tuple(mark.token for mark in VOCABULARY if mark.label in RELAYING)
