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
RELAY_HEADING = "Riding up to your caller, left standing:"

# The notice's three headings. A notice reports rather than instructs, so a
# heading is all the framing each of its groups gets.
SURVIVING_HEADING = "Left standing after the verification pass:"
MENTION_HEADING = "Naming a mark rather than claiming under one, so asked nothing of:"
CITATION_HEADING = "Citing a file nothing in this session opened:"


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
    return f"Resolve each mark, then re-emit the {verb}.\n\n" + "\n\n".join(parts)


def build_context(lines_by_mark):
    """The additionalContext the batch pass hands back mid-turn."""
    return "Resolve each mark now, while the turn is still open.\n\n" + _sections(
        lines_by_mark, MARK_RESOLVE
    )


def build_notice(lines_by_mark, mentions=None, unopened=None, carried=None):
    """The report a Stop pass makes on a surviving mark, a mention or a citation.

    Nothing here asks for a rewrite: the reply this describes already stands.
    A mention costs nothing to write and exempts the line it sits on, so it
    reaches the reader here rather than passing in silence.

    `carried` is the delegate's relay group, which no block carries when the
    pass finds nothing else. Without it a report whose only mark rides up
    produces no output at all, and the question dies where it was written.
    """
    parts = []
    if lines_by_mark:
        parts.append(f"{SURVIVING_HEADING}\n\n" + _listing(lines_by_mark))
    if carried:
        parts.append(f"{RELAY_HEADING}\n\n" + _sections(carried, MARK_CARRY))
    if mentions:
        parts.append(f"{MENTION_HEADING}\n\n" + _listing(mentions))
    if unopened:
        parts.append(
            f"{CITATION_HEADING}\n\n"
            + "\n".join(f"- {citation}" for citation in sorted(unopened.values()))
        )
    return "\n\n".join(parts)
