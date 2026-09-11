"""The messages the hooks hand back when they find a mark.

A mark's resolution class decides which instruction appears, and the tokens
inside the instruction prose come from the vocabulary.
"""

from .marks import CALLER, EVIDENCE, HUMAN, MARK_MEANINGS, holds_class, tokens_of_class

EVIDENCE_MARKS = " or ".join(tokens_of_class(EVIDENCE))
CALLER_MARKS = " or ".join(tokens_of_class(CALLER))
HUMAN_MARKS = " or ".join(tokens_of_class(HUMAN))
RESEARCH_INSTRUCTIONS = (
    "External facts: use a purpose-built research tool (the linkup MCP "
    "tools, the tavily CLI, context7 for library docs). Claims about "
    "local code or files: read the actual source with Read/Grep."
)


def _relay(carried, resolution):
    """The carried lines whose mark resolves the given way, in one flat list."""
    return [line for token in tokens_of_class(resolution) for line in carried.get(token, ())]


def _bulleted(lines):
    return "\n".join(f"- {line}" for line in lines)


def _listing(lines_by_mark):
    """The found lines, grouped under the mark each one carries."""
    return "\n\n".join(
        f"Marked {mark} ({MARK_MEANINGS[mark]}):\n" + "\n".join(f"- {line}" for line in lines)
        for mark, lines in lines_by_mark.items()
    )


def build_reason(lines_by_mark, carried=None, delegate=False):
    """The block message the Stop pass returns on its first pass.

    `carried` holds the relay-class lines a delegate hands upward, keyed by
    mark, and is empty at top level, where the caller is the user and every
    class resolves here.
    """
    carried = carried or {}
    found = ", ".join(lines_by_mark)
    listing = _listing(lines_by_mark)
    steps = []
    if holds_class(lines_by_mark, EVIDENCE):
        steps.append(
            f"For each claim marked {EVIDENCE_MARKS}, gather the evidence that "
            f"would ground it. {RESEARCH_INSTRUCTIONS} Then re-emit the "
            "original reply verbatim, treating each mark as a template "
            "slot. A claim that verified keeps its exact sentence, with "
            "the mark replaced in place by the inline citation: a URL for "
            "an external fact, a path for local code. A claim that "
            "failed verification gets its sentence corrected to what the "
            "evidence supports, or removed if nothing supports it, with a "
            "parenthetical noting the point could not be verified."
        )
    if delegate and holds_class(lines_by_mark, EVIDENCE):
        steps.append(
            f"Where a claim marked {EVIDENCE_MARKS} is still unground when "
            "this pass ends, leave it marked and open the report with "
            "UNANSWERED: each such claim on its own line, the evidence it "
            "waits on, and the lookup already tried. You hold the files and "
            "the tool results, so the caller re-delegates from an explicit "
            "list and re-verifies from a paragraph."
        )
    if holds_class(lines_by_mark, CALLER):
        steps.append(
            f"For each line marked {CALLER_MARKS}, your caller is the user, "
            "so call AskUserQuestion with the question the mark stands in "
            "for and the options you would offer, then re-emit with the "
            "mark dropped, since a live question replaces it. Looking the "
            "premise up settles nothing: only the answer does."
        )
    if holds_class(lines_by_mark, HUMAN):
        steps.append(
            f"For each line marked {HUMAN_MARKS}, call AskUserQuestion with "
            "the question the mark stands in for and the options you would "
            "offer, then re-emit with the mark dropped. A person answers "
            "this mark and nothing else does, so deciding it yourself "
            "leaves it unanswered."
        )
    if _relay(carried, CALLER):
        steps.append(
            f"Leave every line marked {CALLER_MARKS} exactly where it stands, and open "
            "the report with UNANSWERED: the question each one carries and "
            "the options you would have offered, then what you did, then "
            "what you left undone. Calling AskUserQuestion settles nothing "
            "from here, since only whoever spawned you reaches the user, "
            "and they may hold the answer themselves. "
            "The lines that ride up:\n" + _bulleted(_relay(carried, CALLER))
        )
    if _relay(carried, HUMAN):
        steps.append(
            f"Leave every line marked {HUMAN_MARKS} exactly where it stands, and open "
            "the report with UNANSWERED: the question each one carries and "
            "the options you would have offered. Whoever spawned you may "
            "not absorb one of these: a person answers it, so they relay it "
            "through AskUserQuestion and report the answer back. Say so in "
            "the report, so the mark is not mistaken for one the caller "
            "could settle. "
            "The lines that ride up:\n" + _bulleted(_relay(carried, HUMAN))
        )
    steps.append(
        "A flagged line that refers to a mark, rather than claiming under "
        "one, resolves a third way. Keep the reference, name the mark in "
        "words instead of writing the glyph, and say in the same sentence "
        'what you did about it or what you do next: "A subagent returned '
        "a mark handing a decision up to you, so I am putting that "
        'question through AskUserQuestion." A glyph left standing as a '
        "reference identifier reads as a claim awaiting its source, and "
        "this pass cannot tell the two apart."
    )
    steps.append(
        "Change nothing outside the marked sentences: no added commentary, "
        "no report about the verification, no restructuring. The reader "
        "sees the same message they would have seen, with sources where "
        "the marks stood."
    )
    numbered = "\n".join(f"{n}. {step}" for n, step in enumerate(steps, start=1))
    return (
        f"Your reply carries lines marked {found}, each awaiting resolution:\n\n"
        f"{listing}\n\n"
        "Resolve each mark, then re-emit the reply with the marks resolved.\n"
        f"{numbered}"
    )


def build_context(lines_by_mark):
    """The additionalContext the batch pass hands back mid-turn."""
    found = ", ".join(lines_by_mark)
    listing = _listing(lines_by_mark)
    steps = []
    if holds_class(lines_by_mark, EVIDENCE):
        steps.append(
            f"Ground each claim marked {EVIDENCE_MARKS} while the turn is "
            f"still open. {RESEARCH_INSTRUCTIONS} Then give the source in "
            "your next message, a URL for an external fact and a "
            "path for local code, and correct or withdraw any claim "
            "the evidence fails to support."
        )
    if holds_class(lines_by_mark, CALLER):
        steps.append(
            f"For each line marked {CALLER_MARKS}, call AskUserQuestion with the "
            "question the mark stands in for and the options you would "
            "offer, before further work rests on the answer. Looking the "
            "premise up settles nothing: only the answer does."
        )
    if holds_class(lines_by_mark, HUMAN):
        steps.append(
            f"For each line marked {HUMAN_MARKS}, call AskUserQuestion with the "
            "question the mark stands in for, before further work rests on "
            "the answer. A person answers this mark and nothing else does."
        )
    steps.append(
        "A flagged line that refers to a mark, rather than claiming under "
        "one, needs no lookup. Name the mark in words and say what became of it."
    )
    numbered = "\n".join(f"{n}. {step}" for n, step in enumerate(steps, start=1))
    return (
        f"Earlier in this turn you wrote lines marked {found}, each still "
        f"awaiting resolution:\n\n{listing}\n\n"
        "Resolve each one now, so the Stop pass at the end of the turn "
        f"finds nothing left standing.\n{numbered}"
    )


def _flat(lines_by_mark):
    return "\n".join(f"{mark} {line}" for mark, lines in lines_by_mark.items() for line in lines)


def build_notice(lines_by_mark, mentions=None, delegate=False, unopened=None):
    """The systemMessage a Stop pass shows for a surviving mark or a skipped mention.

    A mention costs nothing to write and exempts the line it sits on, so it
    reaches the user here rather than passing in silence.

    The ratchet has one click: this pass never blocks, so a delegate's
    surviving claims would otherwise become the caller's problem in silence.
    Under `delegate` they come back as the report's UNANSWERED opening
    instead, which the caller can re-delegate from.
    """
    parts = []
    if lines_by_mark and delegate:
        parts.append(
            "UNANSWERED: these claims survived the verification pass "
            "unground, and the report hands them on still marked. Open the "
            "report on this list, each claim beside the evidence it waits "
            "on, so the caller re-delegates the lookup rather than repeating "
            "work you were the cheap place to do:\n" + _flat(lines_by_mark)
        )
    elif lines_by_mark:
        parts.append(
            "These marks survived the verification pass and stand as written, "
            "each still awaiting what its mark names:\n" + _flat(lines_by_mark)
        )
    if mentions:
        parts.append(
            "These lines name a mark in words beside the glyph, so the pass "
            "read them as documenting the mark rather than claiming under "
            "it, and asked nothing of them:\n" + _flat(mentions)
        )
    if unopened:
        parts.append(
            "These citations name a file no Read, Grep or Glob of this "
            "session opened, so nothing here shows the claim was checked "
            "against the source it cites:\n"
            + "\n".join(f"- {citation}" for citation in sorted(unopened.values()))
        )
    return "\n\n".join(parts)
