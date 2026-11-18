#!/usr/bin/env python3
"""Rewrites the `deliver.py --part N` entries of `hooks/hooks.json` from `MAX_PARTS`.

Run `python3 lib/rulesets/delivery/hooks_manifest.py` from the plugin root after changing
`MAX_PARTS`. Every other entry and the file's tab indentation stay as they are.
"""

from __future__ import annotations

import json
import pathlib
import shlex
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from rulesets.delivery.parts import MAX_PARTS

HOOKS_JSON = pathlib.Path(__file__).resolve().parents[3] / "hooks" / "hooks.json"
ANNOUNCING_EVENT = "SessionStart"
TIMEOUT_SECONDS = 5


def part_command(part: int, *, announce: bool) -> str:
    flag = "--announce " if announce else ""
    return (
        f'bash "${{CLAUDE_PLUGIN_ROOT}}/hooks/with-python.sh" {flag}'
        f'"${{CLAUDE_PLUGIN_ROOT}}/hooks/deliver.py" --part {part}'
    )


def is_part_entry(hook: dict) -> bool:
    return "--part" in shlex.split(hook["command"])


def part_entries(event: str) -> list[dict]:
    return [
        {
            "type": "command",
            "timeout": TIMEOUT_SECONDS,
            "command": part_command(part, announce=event == ANNOUNCING_EVENT and part == 1),
        }
        for part in range(1, MAX_PARTS + 1)
    ]


def regenerate(manifest_text: str) -> str:
    """The manifest with each group's part entries replaced by parts 1 to `MAX_PARTS`, at the first entry's position."""
    manifest = json.loads(manifest_text)
    for event, groups in manifest["hooks"].items():
        for group in groups:
            rebuilt: list[dict] = []
            placed = False
            for hook in group["hooks"]:
                if not is_part_entry(hook):
                    rebuilt.append(hook)
                elif not placed:
                    rebuilt.extend(part_entries(event))
                    placed = True
            group["hooks"] = rebuilt
    return json.dumps(manifest, indent="\t", ensure_ascii=False) + "\n"


def main() -> int:
    HOOKS_JSON.write_text(regenerate(HOOKS_JSON.read_text(encoding="utf-8")), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
