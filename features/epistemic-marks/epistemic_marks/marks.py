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
            "Gather the evidence for each claim below now: read the code it "
            "describes or fetch the page it rests on. Replace the mark in place "
            "with that source, a path with its line or a URL. Narrow a claim the "
            "evidence narrows. Remove a claim the evidence contradicts."
        ),
        carry=(
            "Keep each claim below marked. Open your report on it, stating the "
            "evidence it waits on and the lookup you already tried."
        ),
    ),
    Mark(
        token="[.?]",
        label=NEEDS_VERIFICATION,
        name="the secondhand mark",
        resolve=(
            "Check each relayed claim below against its own source now. Where the "
            "claim came with a citation, write that citation in place of the mark. "
            "Where it came without one, ask the delegate that wrote it for the "
            "source, or find the source yourself. Narrow or remove a claim the "
            "source does not back."
        ),
        carry=(
            "Keep each claim below marked. Open your report on it, naming the "
            "source that would settle it."
        ),
    ),
    Mark(
        token="[^?]",
        label=ESCALATE_DECISION,
        name="the caller's mark",
        resolve=(
            "Put the question behind each line below to your caller now, with the "
            "options you would offer. Replace the mark with the answer."
        ),
        carry=(
            "Leave each line below exactly as it stands. Open your report on the "
            "question it carries, with the options you would have offered."
        ),
    ),
    Mark(
        token="[!?]",
        label=ASK_USER,
        name="the standing question",
        resolve=(
            "Put the question behind each line below to a person now, with the "
            "options you would offer. Replace the mark with their answer, and "
            "never answer it yourself."
        ),
        carry=(
            "Leave each line below exactly as it stands, since only a person "
            "answers it. Open your report on the question it carries, with the "
            "context a person needs to decide it."
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
