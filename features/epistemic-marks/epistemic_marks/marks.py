"""The epistemic-mark vocabulary these hooks enforce.

Every other module reads the vocabulary from here and writes no mark token as
a literal. tests/test_marks_vocabulary.py compares it against the rule text
that teaches it.
"""

from dataclasses import dataclass

EVIDENCE = "evidence"
ASK = "ask"


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
        name="the user's mark",
        gloss="awaits an answer only the user supplies",
        resolution=ASK,
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


ASK_MARK = next(iter(tokens_of_class(ASK)), None)
