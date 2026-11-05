"""An adopted manifest written as YAML."""

from __future__ import annotations

import json
from collections.abc import Iterable

from rulesets.adopt.mapping import Block


def _flow(items: Iterable[str]) -> str:
    return "[" + ", ".join(json.dumps(item) for item in items) + "]"


def manifest_text(models: tuple[str, ...], blocks: tuple[Block, ...]) -> str:
    """`models` where any are declared, `defaults` spreading every rule, and one `when` item per block."""

    lines = [f"models: {_flow(models)}"] if models else []
    lines.append(f"defaults: {_flow(['all:*'])}")
    if blocks:
        lines.append("when:")
        lines.extend(f"  - {json.dumps(b.condition)}: {_flow(b.entries)}" for b in blocks)
    return "\n".join(lines) + "\n"
