"""The epistemic-mark vocabulary these hooks enforce.

Every other module reads the vocabulary from here and writes no mark token as
a literal. tests/test_marks_vocabulary.py compares it against the rule text
that teaches it.
"""

from dataclasses import dataclass

EVIDENCE = "evidence"
CALLER = "caller"
HUMAN = "human"

# The classes whose answer sits outside the agent that wrote the mark, so a
# delegate's Stop pass carries them to the caller rather than blocking on
# them. Every class that is not EVIDENCE belongs here, and
# tests/test_marks_vocabulary.py fails on one that does not.
RELAY = (CALLER, HUMAN)


@dataclass(frozen=True)
class Mark:
    token: str
    name: str
    gloss: str
    resolution: str


VOCABULARY = (
    Mark(
        token="[?]",
        name="the unsourced mark",
        gloss="no source on file",
        resolution=EVIDENCE,
    ),
    Mark(
        token="[.?]",
        name="the secondhand mark",
        gloss="secondhand and ungrounded",
        resolution=EVIDENCE,
    ),
    Mark(
        token="[^?]",
        name="the caller's mark",
        gloss="awaits an answer whoever spawned you can settle",
        resolution=CALLER,
    ),
    Mark(
        token="[!?]",
        name="the standing question",
        gloss="awaits an answer only a person supplies",
        resolution=HUMAN,
    ),
)

MARKS = tuple(mark.token for mark in VOCABULARY)

MARK_MEANINGS = {mark.token: mark.gloss for mark in VOCABULARY}

MARK_NAMES = {mark.token: mark.name for mark in VOCABULARY}


def tokens_of_class(resolution):
    """The tokens whose resolution takes the given form."""
    return tuple(mark.token for mark in VOCABULARY if mark.resolution == resolution)


def holds_class(lines_by_mark, resolution):
    """Whether any mark found in the reply resolves the given way."""
    return any(token in lines_by_mark for token in tokens_of_class(resolution))


# Every token a delegate hands upward instead of resolving itself. A single
# token would drop the second one silently, which is what the split of the
# escalation mark into a caller's mark and a standing question introduced.
RELAY_MARKS = tuple(token for resolution in RELAY for token in tokens_of_class(resolution))
