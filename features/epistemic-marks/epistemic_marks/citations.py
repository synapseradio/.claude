"""Checking a reply's citations against the files the session actually opened.

Once a citation is what marks a checked claim, a fabricated citation is the
cheapest way to look verified, so requiring citations without checking them
rewards inventing them. This module finds a `path:line` citation in a reply
and asks whether any Read, Grep or Glob of the session ever surfaced that
path.

It never blocks. It fires on citations the agent wrote itself, so it carries
none of the false-positive load of judging whether a turn gathered enough
evidence, and the worst case is one notice a reader can dismiss.
"""

import json
import os
import re

from .scan import fenced_line_numbers

# The tools that put a file in front of the agent. A path a Bash command
# merely listed is not a file anybody read, so those calls do not count.
OPENING_TOOLS = ("Read", "Grep", "Glob")

# A path with an extension, followed by a line or a line range. The extension
# has to start with a letter, which keeps a clock time and a version number
# out. The lookbehind keeps the host of a `scheme://host.tld:port` out, since
# the character before it is a slash.
CITATION = re.compile(r"(?<![\w/.~-])((?:[\w.~-]+/)*[\w~-]+\.[A-Za-z]\w*):\d+(?:-\d+)?(?![\w:])")

# Past this, one linear pass costs more than the notice is worth, so the
# check fails open and the reply passes unremarked.
MAX_TRANSCRIPT_BYTES = 32 * 1024 * 1024


def cited_paths(blocks):
    """Every `path:line` citation in the reply, keyed by its path.

    Fenced code is skipped, since a `file.py:12` inside an example block is
    part of the example rather than a claim about this repository.
    """
    lines = [line for block in blocks for line in block.splitlines()]
    fenced = fenced_line_numbers(lines)
    found = {}
    for number, line in enumerate(lines):
        if number in fenced:
            continue
        for match in CITATION.finditer(line):
            found.setdefault(match.group(1), match.group(0))
    return found


def _opened_text(entry, opening_ids):
    """The text an opening tool's call or its result carried in this entry.

    The assistant's own prose is left out on purpose: a reply citing a path
    would otherwise confirm itself.
    """
    message = entry.get("message")
    content = message.get("content") if isinstance(message, dict) else None
    if not isinstance(content, list):
        return
    for block in content:
        if not isinstance(block, dict):
            continue
        if block.get("type") == "tool_use" and block.get("name") in OPENING_TOOLS:
            opening_ids.add(block.get("id"))
            yield json.dumps(block.get("input", {}))
        elif block.get("type") == "tool_result" and block.get("tool_use_id") in opening_ids:
            payload = block.get("content")
            yield payload if isinstance(payload, str) else json.dumps(payload)


def unopened(blocks, transcript_path):
    """The reply's citations naming a path no Read, Grep or Glob of the session surfaced.

    A path matches by substring, so a relative citation matches the absolute
    path a tool call carried, and a path a Grep or Glob listed in its results
    counts as surfaced. That direction is deliberate: an extra match costs a
    missed notice, and a missed match costs a reader a false accusation.
    """
    candidates = cited_paths(blocks)
    if not candidates or not transcript_path:
        return {}
    try:
        if os.path.getsize(transcript_path) > MAX_TRANSCRIPT_BYTES:
            return {}
    except OSError:
        return {}

    opening_ids = set()
    try:
        with open(transcript_path, "rb") as f:
            for raw_line in f:
                if not candidates:
                    break
                try:
                    entry = json.loads(raw_line)
                except ValueError:
                    continue
                for text in _opened_text(entry, opening_ids):
                    for path in [p for p in candidates if p in text]:
                        del candidates[path]
    except OSError:
        return {}
    return candidates
