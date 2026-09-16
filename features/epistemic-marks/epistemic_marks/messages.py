"""The messages the hooks hand back when they find a mark.

The rule owns what a mark means; these builders own what to do about one. A
sentence stating a mark's meaning here would be the rule restated, so the
glosses live in the rule text alone and each mark carries its own act.

Every string here is read by an agent on a machine whose toolset this plugin
cannot know, so no generated line names a tool. Each line phrases the act to
perform rather than the call to make.
"""

from .marks import MARK_CARRY, MARK_RESOLVE

# A group heading the marks cannot carry, since only the hook knows this pass
# is a delegate's and that these lines reach no further from here.
RELAY_HEADING = "Someone above you settles these. Carry each one up in your report:"

# The notice's two headings. Each group states what it found, then what to do
# about it, since the agent reading it is still able to act.
SURVIVING_HEADING = "Still marked after the verification pass:"
MENTION_HEADING = "Naming a mark in code rather than claiming under it, so left unchecked:"

# The act for a mention, which no mark record can carry: a mention is exempt
# by its form, and only the writer knows whether the line also claims.
MENTION_ACT = (
    "Check each line below now. Where it states a claim of its own, resolve "
    "that claim. Where it only names the mark, say in the same sentence what "
    "became of the mark."
)


def _listing(lines_by_mark):
    """The found lines, grouped under the glyph each one carries."""
    return "\n\n".join(
        f"{mark}\n" + "\n".join(f"- {line}" for line in lines)
        for mark, lines in lines_by_mark.items()
    )


def _sections(lines_by_mark, instruction):
    """One subsection per detected mark: the glyph, its act, then its lines.

    Iterating the marks found rather than the vocabulary is what keeps a
    reply carrying one mark from reading an instruction about another.
    """
    return "\n\n".join(
        f"{mark}\n{instruction[mark]}\n" + "\n".join(f"- {line}" for line in lines)
        for mark, lines in lines_by_mark.items()
    )


def build_reason(lines_by_mark, carried=None, delegate=False):
    """The block message the Stop pass returns on its first pass.

    `carried` holds the lines a delegate hands upward, keyed by mark, and is
    empty at top level, where the caller is the user and every mark resolves
    here. `delegate` picks the noun for what gets re-emitted and nothing else.
    """
    parts = [_sections(lines_by_mark, MARK_RESOLVE)] if lines_by_mark else []
    if carried:
        parts.append(f"{RELAY_HEADING}\n\n" + _sections(carried, MARK_CARRY))
    verb = "report" if delegate else "reply"
    return (
        f"Your {verb} still carries unresolved marks. Before you stop, act on "
        f"each group below, then re-emit the whole {verb}.\n\n" + "\n\n".join(parts)
    )


def build_context(lines_by_mark):
    """The additionalContext the batch pass hands back mid-turn.

    Stated as a finding followed by its act, since additionalContext framed as
    an out-of-band command can read as an injection, per
    https://code.claude.com/docs/en/hooks
    """
    return (
        "Text written earlier in this turn carries the marks below. Resolve "
        "each one before your next step.\n\n" + _sections(lines_by_mark, MARK_RESOLVE)
    )


def build_notice(lines_by_mark, mentions=None, carried=None):
    """The report a Stop pass makes on a surviving mark or a mention.

    Each group carries its act. A surviving mark takes the carry act, since
    the pass that could resolve it already ran. A delegate reads this as
    additionalContext and can still write the item into its report. At top
    level it goes to the user as a systemMessage, where the act says what the
    reply left undone. A mention costs nothing to write and exempts the line
    it sits on, so it reaches the reader here rather than passing in silence.

    `carried` is the delegate's relay group, which no block carries when the
    pass finds nothing else. Without it a report whose only mark rides up
    produces no output at all, and the question dies where it was written.
    """
    parts = []
    if lines_by_mark:
        parts.append(f"{SURVIVING_HEADING}\n\n" + _sections(lines_by_mark, MARK_CARRY))
    if carried:
        parts.append(f"{RELAY_HEADING}\n\n" + _sections(carried, MARK_CARRY))
    if mentions:
        parts.append(f"{MENTION_HEADING}\n{MENTION_ACT}\n\n" + _listing(mentions))
    return "\n\n".join(parts)
