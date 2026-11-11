"""An adopted config written in the config layout: words, and one block per condition."""

from __future__ import annotations

from rulesets.adopt.mapping import Block


def _list(key: str, words: tuple[str, ...]) -> list[str]:
    """A block's list under `key`, one word per line."""

    return [f"  {key}:", *(f"    {word}" for word in words)] if words else []


def config_text(models: tuple[str, ...], blocks: tuple[Block, ...]) -> str:
    """`models` where any are declared, `defaults` spreading every rule, and each block in turn."""

    lines = [f"models: {' '.join(models)}"] if models else []
    lines.append("defaults: all.*")
    for block in blocks:
        lines.append(f"{block.condition}:")
        lines.extend(_list("include", block.include))
        lines.extend(_list("exclude", block.exclude))
    return "\n".join(lines) + "\n"
