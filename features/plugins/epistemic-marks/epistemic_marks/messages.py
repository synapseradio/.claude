"""The messages the hooks hand back when they find a mark or a guess in words.

The rule owns what a mark means; these builders own what to do about one. A
sentence stating a mark's meaning here would be the rule restated, so the
glosses live in the rule text alone and each mark carries its own act.

Every string here is read by an agent on a machine whose toolset this plugin
cannot know, so no generated line names a tool. Each line phrases the act to
perform rather than the call to make.
"""

from .hedges import ASKED, CAUSE, GUESS, REST, SAID
from .marks import (
    MARK_CARRY,
    MARK_RESOLVE,
    NEEDS_CITATION,
    NEEDS_VERIFICATION,
    VOCABULARY,
)

# The mark a guess takes once it is written as a claim, read from the
# vocabulary so no token is spelled out here.
UNSOURCED = next(mark.token for mark in VOCABULARY if mark.label == NEEDS_CITATION)
SECONDHAND = next(mark.token for mark in VOCABULARY if mark.label == NEEDS_VERIFICATION)

# A guess in words has no glyph to head its group, so each kind gets a
# heading, and the two acts a mark record would have carried.
WORDING_HEADING = {
    GUESS: "Guessed in words, unmarked:",
    CAUSE: "A cause stated with no source and no mark:",
    REST: "Built on a guess, unmarked:",
    ASKED: "A claim carried in a question:",
    SAID: "Laid on the user, without their words:",
}

# The fourth sentence closes the cheapest way out. A writer told only that a
# hedge was found deletes the word and keeps the guess, which then reads as a
# finding.
WORDING_RESOLVE = {
    GUESS: (
        "Each line below guesses in words, with no mark and no source. Check the "
        "claim now and put its source beside it, a path with its line or a URL. "
        f"Where no check reaches it, state it plainly and end its clause with {UNSOURCED}. "
        "Without the hedge word it is still a guess. Quote words that are someone else's."
    ),
    CAUSE: (
        "Each line below says why something fails. Put the source that shows it "
        "beside it, a path with its line or a URL. Where you reasoned your way to "
        f"it, end its clause with {UNSOURCED}."
    ),
    REST: (
        "Each line below builds on the guess or marked claim before it. End its "
        "clause with the same mark, or put its own source beside it."
    ),
    ASKED: (
        "Each line below asserts something in the form of a question. State the "
        f"claim on its own, with its source or with {UNSOURCED} ending its clause, "
        "then ask only what you want answered."
    ),
    SAID: (
        "Each line below reports what the user said. Put their words from this "
        "conversation beside it in quotation marks. Where you hold no words to "
        f"quote, end its clause with {SECONDHAND}."
    ),
}

WORDING_CARRY = {
    GUESS: (
        "Each line below still guesses in words. End its clause with "
        f"{UNSOURCED} and open your report on it."
    ),
    CAUSE: (
        f"Each line below still states a cause nobody sourced. End its clause with {UNSOURCED} "
        "and open your report on it."
    ),
    REST: (
        "Each line below still builds on an unchecked claim. End its clause with that claim's mark."
    ),
    ASKED: (
        "Each line below still asserts through a question. State the claim and "
        f"end its clause with {UNSOURCED}."
    ),
    SAID: (
        "Each line below still reports the user's statement without their words. "
        f"End its clause with {SECONDHAND}."
    ),
}

# A group heading the marks cannot carry, since only the hook knows this pass
# is a delegate's and that these lines reach no further from here.
RELAY_HEADING = "Someone above you settles these. Carry each one up in your report:"

# The notice's two headings. Each group states what it found, then what to do
# about it, since the agent reading it is still able to act.
SURVIVING_HEADING = "Still marked after the verification pass:"

# The heading a later pass blocks under when a line already sent back once
# still stands and the reply does not open on it. It states the check the
# hook runs, so the reader knows what passes it: verify-marks.py reads the
# reply's leading lines, skipping headings and labels ending in a colon.
STANDING_HEADING = (
    "Still marked after the verification pass. Open your {verb} on these lines: "
    "put each one ahead of every line that carries no mark, with at most a "
    "heading or a label ending in a colon above them."
)
MENTION_HEADING = "Naming a mark in code rather than claiming under it, so left unchecked:"

# The act for a mention, which no mark record can carry: a mention is exempt
# by its form, and only the writer knows whether the line also claims.
MENTION_ACT = (
    "Check each line below now. Where it states a claim of its own, resolve "
    "that claim. Where it only names the mark, say in the same sentence what "
    "became of the mark."
)


def _listing(lines_by_mark) -> str:
    """The found lines, grouped under the glyph each one carries."""
    return "\n\n".join(
        f"{mark}\n" + "\n".join(f"- {line}" for line in lines)
        for mark, lines in lines_by_mark.items()
    )


def _sections(lines_by_mark, instruction) -> str:
    """One subsection per detected mark: the glyph, its act, then its lines.

    Iterating the marks found rather than the vocabulary is what keeps a
    reply carrying one mark from reading an instruction about another.
    """
    return "\n\n".join(
        f"{mark}\n{instruction[mark]}\n" + "\n".join(f"- {line}" for line in lines)
        for mark, lines in lines_by_mark.items()
    )


def _wording_sections(wording, instruction) -> str:
    """One subsection per kind of guess found: its heading, its act, then its lines."""
    return "\n\n".join(
        f"{WORDING_HEADING[kind]}\n{instruction[kind]}\n" + "\n".join(f"- {line}" for line in lines)
        for kind, lines in wording.items()
    )


def _resolving(lines_by_mark, wording) -> list[str]:
    """The groups a pass asks to settle now, guesses in words first."""
    parts = [_wording_sections(wording, WORDING_RESOLVE)] if wording else []
    if lines_by_mark:
        parts.append(_sections(lines_by_mark, MARK_RESOLVE))
    return parts


def _mention_part(mentions) -> str:
    """The mention group: its heading, its act, then its lines."""
    return f"{MENTION_HEADING}\n{MENTION_ACT}\n\n" + _listing(mentions)


def build_reason(
    lines_by_mark, carried=None, delegate=False, wording=None, standing=None, mentions=None
) -> str:
    """The block message a Stop pass returns.

    `carried` holds the lines a delegate hands upward, keyed by mark, and is
    empty at top level, where the caller is the user and every mark resolves
    here. `delegate` picks the noun for what gets re-emitted.
    `wording` holds the sentences that guess in words, keyed by kind.
    `standing` holds the lines a block already sent back once, which a later
    pass found still marked and not yet opened on, keyed by mark.
    `mentions` holds the lines naming a mark rather than claiming under it,
    which ride in the block so the model reads them in the same message.
    """
    verb = "report" if delegate else "reply"
    parts = _resolving(lines_by_mark, wording)
    if standing:
        parts.append(STANDING_HEADING.format(verb=verb) + "\n\n" + _sections(standing, MARK_CARRY))
    if carried:
        parts.append(f"{RELAY_HEADING}\n\n" + _sections(carried, MARK_CARRY))
    if mentions:
        parts.append(_mention_part(mentions))
    return (
        f"Your {verb} carries unchecked claims. Act on each group below, then "
        f"re-emit the whole {verb}.\n\n" + "\n\n".join(parts)
    )


def build_context(lines_by_mark, wording=None) -> str:
    """The additionalContext the batch pass hands back mid-turn.

    Stated as a finding followed by its act, since additionalContext framed as
    an out-of-band command can read as an injection, per
    https://code.claude.com/docs/en/hooks
    """
    return (
        "Text written earlier in this turn carries unchecked claims. Act on each "
        "group below before your next step, and build nothing on them until then.\n\n"
        + "\n\n".join(_resolving(lines_by_mark, wording))
    )


def build_denial(wording) -> str:
    """The reason a spawn call is denied when its prompt guesses in words.

    A delegate reads a prompt as its ground truth, so a guess there is acted
    on as a finding. A marked claim travels: the mark tells the delegate what
    is unverified.
    """
    return (
        "This prompt hands a delegate a guess as a finding. Act on each group "
        "below, then send the prompt again.\n\n" + _wording_sections(wording, WORDING_RESOLVE)
    )


def build_notice(lines_by_mark, mentions=None, carried=None, wording=None) -> str:
    """The report a Stop pass makes on a surviving mark or a mention.

    Each group carries its act. A surviving mark takes the carry act, since
    the pass that could resolve it already ran. The model reads this as
    additionalContext and can still write each item into its reply or
    report, and the user sees the same text. A mention costs nothing to
    write and exempts the line it sits on, so it reaches the reader here
    rather than passing in silence.

    `carried` is the delegate's relay group, which no block carries when the
    pass finds nothing else. Without it a report whose only mark rides up
    produces no output at all, and the question dies where it was written.
    """
    parts = [_wording_sections(wording, WORDING_CARRY)] if wording else []
    if lines_by_mark:
        parts.append(f"{SURVIVING_HEADING}\n\n" + _sections(lines_by_mark, MARK_CARRY))
    if carried:
        parts.append(f"{RELAY_HEADING}\n\n" + _sections(carried, MARK_CARRY))
    if mentions:
        parts.append(_mention_part(mentions))
    return "\n\n".join(parts)
