"""The messages the hooks hand back when they find a mark.

A mark's resolution class decides which instruction appears, and the tokens
inside the instruction prose come from the vocabulary.
"""

from .marks import ASK, ASK_MARK, EVIDENCE, MARK_MEANINGS, holds_class, tokens_of_class

EVIDENCE_MARKS = " or ".join(tokens_of_class(EVIDENCE))
RESEARCH_INSTRUCTIONS = (
    "External facts: use a purpose-built research tool (the linkup MCP "
    "tools, the tavily CLI, context7 for library docs). Claims about "
    "local code or files: read the actual source with Read/Grep."
)


def _listing(lines_by_mark):
    """The found lines, grouped under the mark each one carries."""
    return "\n\n".join(
        f"Marked {mark} ({MARK_MEANINGS[mark]}):\n" + "\n".join(f"- {line}" for line in lines)
        for mark, lines in lines_by_mark.items()
    )


def build_reason(lines_by_mark, carried=()):
    """The block message the Stop pass returns on its first pass."""
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
            "an external fact, a path:line for local code. A claim that "
            "failed verification gets its sentence corrected to what the "
            "evidence supports, or removed if nothing supports it, with a "
            "parenthetical noting the point could not be verified."
        )
    if holds_class(lines_by_mark, ASK):
        steps.append(
            f"For each line marked {ASK_MARK}, call AskUserQuestion with the "
            "question the mark stands in for and the options you would "
            "offer, then re-emit with the mark dropped, since a live "
            "question replaces it. Looking the premise up settles nothing: "
            "only the user's answer does."
        )
    if carried:
        steps.append(
            f"Leave every line marked {ASK_MARK} exactly where it stands, and open "
            "the report with UNANSWERED: the question each one carries and "
            "the options you would have offered, then what you did, then "
            "what you left undone. Calling AskUserQuestion settles nothing "
            "from here, since only whoever spawned you reaches the user. "
            "The lines that ride up:\n" + "\n".join(f"- {line}" for line in carried)
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
            "path:line for local code, and correct or withdraw any claim "
            "the evidence fails to support."
        )
    if holds_class(lines_by_mark, ASK):
        steps.append(
            f"For each line marked {ASK_MARK}, call AskUserQuestion with the "
            "question the mark stands in for and the options you would "
            "offer, before further work rests on the answer. Looking the "
            "premise up settles nothing: only the user's answer does."
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


def build_notice(lines_by_mark):
    """The systemMessage a second Stop pass shows for a surviving mark."""
    listing = "\n".join(f"{mark} {line}" for mark, lines in lines_by_mark.items() for line in lines)
    return (
        "These marks survived the verification pass and stand as written, "
        "each still awaiting what its mark names:\n" + listing
    )
