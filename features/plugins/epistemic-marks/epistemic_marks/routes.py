"""Finding a fetch a permission check denied, with a mark written after it and no other route tried.

A denied fetch closes one route to a source and leaves the source itself
unread. The rule text sends the writer down every other route in reach before
a mark may stand in the source's place. No hook can know every route a
machine offers, so this scan holds the floor: a turn whose last fetch was
denied on its first try, followed by a mark and by no second try.

A second fetch after the denial, whatever its result, ends the finding, since
from there the rule text carries the duty to try every route and name each
one tried. A person's refusal of a tool call writes other words to the
transcript and never matches DENIAL, so no finding sends a writer around it.
"""

import re

from .marks import NEEDS_CITATION, NEEDS_VERIFICATION, VOCABULARY
from .scan import marked_lines, text_blocks

# The tool-result text of a call a permission check denied. The auto mode
# classifier writes the first, a permission rule the second.
DENIAL = re.compile(
    r"denied by the Claude Code auto mode classifier|Permission for this action was denied",
    re.IGNORECASE,
)

# A tool whose name says it reads a page from the network, such as a fetch,
# an extract, a scrape or a crawl tool from any server.
FETCH_TOOL = re.compile(r"fetch|extract|scrape|crawl|browse", re.IGNORECASE)

# A shell command that reads from the network.
FETCH_COMMAND = re.compile(r"\b(?:curl|wget|tvly)\b|https?://")

# The marks a claim takes in place of its source. A decision mark asks a
# question rather than standing in for a source, so it never counts here.
SOURCE_MARKS = tuple(
    mark.token for mark in VOCABULARY if mark.label in {NEEDS_CITATION, NEEDS_VERIFICATION}
)

LABEL_LENGTH = 200


def _route(block) -> str | None:
    """How a tool call reaches the network, or None where it does not."""
    name = block.get("name")
    tool_input = block.get("input")
    if not isinstance(name, str) or not isinstance(tool_input, dict):
        return None
    if name == "Bash":
        command = tool_input.get("command")
        if isinstance(command, str) and FETCH_COMMAND.search(command):
            return command[:LABEL_LENGTH]
        return None
    if not FETCH_TOOL.search(name):
        return None
    target = next((value for value in tool_input.values() if isinstance(value, str)), "")
    return f"{name} {target}".strip()[:LABEL_LENGTH]


def _result_text(block) -> str:
    content = block.get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(
            part.get("text", "")
            for part in content
            if isinstance(part, dict) and part.get("type") == "text"
        )
    return ""


def _blocks(entry) -> list[dict]:
    content = entry.get("message", {}).get("content")
    if not isinstance(content, list):
        return []
    return [block for block in content if isinstance(block, dict)]


def denied_routes(entries, reply, *, drafts) -> list[str]:
    """The denied fetch the turn wrote a mark after with no other fetch tried, as one label.

    `entries` holds the turn's assistant entries and tool results in order.
    `reply` is the final reply, which may not have reached the transcript
    yet. With `drafts` the assistant text the turn wrote after the denial
    counts alongside the reply; without it the reply alone counts, as on a
    later pass, where the earlier text is a draft the reply replaced.

    The list is empty, or holds the label of the turn's last fetch, where
    that fetch was denied, the fetch before it (if any) went through, and a
    source mark sits in the text after it.
    """
    fetches = []  # (call id, label), in call order
    denied = set()
    text_after = {}  # call id -> assistant text written after its denial
    for entry in entries:
        for block in _blocks(entry):
            kind = block.get("type")
            if kind == "tool_use" and (label := _route(block)) is not None:
                fetches.append((block.get("id"), label))
            elif kind == "tool_result" and DENIAL.search(_result_text(block)):
                denied.add(block.get("tool_use_id"))
                text_after.setdefault(block.get("tool_use_id"), [])
        if entry.get("type") == "assistant":
            for call_id in text_after:
                text_after[call_id].extend(text_blocks(entry.get("message", {})))
    if not fetches:
        return []
    last_id, last_label = fetches[-1]
    if last_id not in denied:
        return []
    if len(fetches) > 1 and fetches[-2][0] in denied:
        return []
    texts = [*(text_after.get(last_id, []) if drafts else []), reply]
    found, _ = marked_lines(texts)
    if not any(mark in found for mark in SOURCE_MARKS):
        return []
    return [last_label]
