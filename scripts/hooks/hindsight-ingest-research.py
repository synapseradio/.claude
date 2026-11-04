#!/usr/bin/env python3
"""PostToolUse hook: retain a research note into the session's Hindsight bank.

A Markdown file whose frontmatter sets `kind: research` is retained under the
bank's `research` retain strategy, tagged `source:research`, with the
frontmatter's `entities` list resolved against the entities the bank already
holds, so the note links to the facts and observations that name them.

The bank is the one the hindsight-coding-agents plugin resolves for the
session's working directory, read from its status script, so a note saved in
the scratchpad still lands in the bank of the repository the session works
in. The document id is `research:<file stem>`, and saving the note again
replaces the earlier version.

The hook never blocks the tool call: any failure prints one line to stderr
and exits 0.
"""

import json
import os
import re
import subprocess
import sys
import urllib.error
from pathlib import Path

# Run under `python -I`, which leaves the script's directory off sys.path.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from hindsight_research_bank import STRATEGY_NAME, ensure_strategy, request, resolve_bank

FRONTMATTER = re.compile(r"\A---\n(.*?)\n---\n", re.DOTALL)


def parse_frontmatter(text):
    """Reads the flat keys and string lists this hook needs from YAML frontmatter."""
    match = FRONTMATTER.match(text)
    if not match:
        return {}
    fields = {}
    current_list = None
    for line in match.group(1).splitlines():
        item = re.match(r"^\s+-\s+(.*)$", line)
        if item and current_list is not None:
            current_list.append(item.group(1).strip().strip("'\""))
            continue
        pair = re.match(r"^([A-Za-z_][\w-]*):\s*(.*)$", line)
        if not pair:
            current_list = None
            continue
        key, value = pair.group(1), pair.group(2).strip()
        if value.startswith("[") and value.endswith("]"):
            fields[key] = [v.strip().strip("'\"") for v in value[1:-1].split(",") if v.strip()]
            current_list = None
        elif value == "":
            fields[key] = []
            current_list = fields[key]
        else:
            fields[key] = value.strip("'\"")
            current_list = None
    return fields


def retain(bank, path, text, fields):
    entities = fields.get("entities") or []
    if isinstance(entities, str):
        entities = [entities]
    item = {
        "content": text,
        "document_id": f"research:{path.stem}",
        "context": f"research note {path.name}",
        "metadata": {"source": "research", "path": str(path)},
        "tags": ["source:research"],
        "entities": [{"text": name} for name in entities],
        "resolve_entities": True,
        "observation_scopes": "shared",
        "strategy": STRATEGY_NAME,
    }
    request("POST", f"/v1/default/banks/{bank}/memories", {"items": [item], "async": True})


def main():
    payload = json.load(sys.stdin)
    file_path = (payload.get("tool_input") or {}).get("file_path") or ""
    if not file_path.endswith(".md"):
        return
    path = Path(file_path)
    text = path.read_text(encoding="utf-8")
    fields = parse_frontmatter(text)
    if fields.get("kind") != "research":
        return
    bank = resolve_bank(payload.get("cwd") or os.getcwd())
    ensure_strategy(bank)
    retain(bank, path, text, fields)
    print(f"Research note {path.name} queued for Hindsight bank {bank}.", file=sys.stderr)


if __name__ == "__main__":
    try:
        main()
    except (
        OSError,
        ValueError,
        KeyError,
        subprocess.SubprocessError,
        urllib.error.URLError,
    ) as error:
        print(f"hindsight-ingest-research: {error}", file=sys.stderr)
    sys.exit(0)
