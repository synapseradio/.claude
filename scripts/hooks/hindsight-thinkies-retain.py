#!/usr/bin/env python3
"""Stop hook: retain the turn's thinkies output into me::thinkies and the repo's bank.

A turn counts as thinkies output when it ran the Skill tool on a thinkies:* skill,
or when its user message was a /thinkies:* slash command. The retained content is
the assistant text written after that point in the turn. It goes to me::thinkies
and, inside a git repository, to coding-agent::<repo> as well, both under one
document id, so recall from either bank finds it. Any failure exits 0 silently.
"""

import contextlib
import json
import re
import sys

from hindsight_retain import repo_name, retain

MAX_CHARS = 60_000
SLASH = re.compile(r"<command-name>/(thinkies:[\w-]+)</command-name>")


def entries(path):
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            try:
                yield json.loads(line)
            except ValueError:
                continue


def is_prompt(entry):
    """A user entry the person typed, as opposed to a tool result or meta injection."""
    return (
        entry.get("type") == "user"
        and not entry.get("isMeta")
        and isinstance(entry.get("message", {}).get("content"), str)
    )


def last_turn(path):
    turn = []
    for entry in entries(path):
        if is_prompt(entry):
            turn = []
        turn.append(entry)
    return turn


def thinkies_output(turn):
    """(skill, anchor id, text) for the turn's thinkies run, or None."""
    skill = anchor = None
    texts = []
    if turn and is_prompt(turn[0]):
        match = SLASH.search(turn[0]["message"]["content"])
        if match:
            skill, anchor = match.group(1), turn[0].get("uuid", "prompt")
    for entry in turn:
        if entry.get("type") != "assistant":
            continue
        for block in entry.get("message", {}).get("content") or []:
            if block.get("type") == "tool_use" and block.get("name") == "Skill":
                name = (block.get("input") or {}).get("skill", "")
                if name.startswith("thinkies:"):
                    skill, anchor, texts = name, block.get("id"), []
            elif block.get("type") == "text" and skill:
                texts.append(block.get("text", ""))
    text = "\n\n".join(t for t in texts if t.strip())
    return (skill, anchor, text) if skill and text else None


def main():
    payload = json.load(sys.stdin)
    if payload.get("stop_hook_active"):
        return
    found = thinkies_output(last_turn(payload["transcript_path"]))
    if not found:
        return
    skill, anchor, text = found
    repo = repo_name(payload.get("cwd") or ".")
    document_id = f"thinkies:{payload.get('session_id', 'session')}:{anchor}"
    tags = ["source:thinkies", f"skill:{skill}", f"repo:{repo or 'none'}"]
    content = f"Output of the {skill} skill.\n\n{text[:MAX_CHARS]}"
    banks = ["me::thinkies"] + ([f"coding-agent::{repo}"] if repo else [])
    for bank in banks:
        retain(bank, content, document_id, tags, context=f"thinkies output from {skill}")


if __name__ == "__main__":
    with contextlib.suppress(Exception):
        main()
