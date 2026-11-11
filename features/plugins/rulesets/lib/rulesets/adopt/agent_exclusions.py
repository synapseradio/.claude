"""Agent definitions read for the rules they exclude, and those exclusions as config blocks."""

from __future__ import annotations

import dataclasses
import pathlib
from collections.abc import Collection, Iterable

import yaml

from rulesets.adopt.mapping import Block
from rulesets.documents import split_frontmatter


@dataclasses.dataclass(frozen=True)
class AgentDefinition:
    """An agent's registered name and the stems its `metadata.rulesets.exclude` lists."""

    name: str
    excluded: tuple[str, ...]


def _excluded(front: dict) -> tuple[str, ...]:
    metadata = front.get("metadata")
    block = metadata.get("rulesets") if isinstance(metadata, dict) else None
    listed = block.get("exclude") if isinstance(block, dict) else None
    if not isinstance(listed, list):
        return ()
    return tuple(stem for stem in listed if isinstance(stem, str))


def read_definitions(agents: pathlib.Path) -> tuple[AgentDefinition, ...]:
    """Every definition under the `agents` directory, sorted by name.

    A definition registers under its `name` field, or under its file name where it names none.
    """

    found: list[AgentDefinition] = []
    for path in sorted(agents.rglob("*.md")) if agents.is_dir() else ():
        split = split_frontmatter(path.read_bytes().decode("utf-8", errors="replace"))
        try:
            front = yaml.safe_load(split[0]) if split else {}
        except yaml.YAMLError:
            continue
        if not isinstance(front, dict):
            continue
        name = front.get("name")
        found.append(
            AgentDefinition(name if isinstance(name, str) and name else path.stem, _excluded(front))
        )
    return tuple(sorted(found, key=lambda definition: definition.name))


def exclusion_blocks(
    definitions: Iterable[AgentDefinition], rules: Collection[str]
) -> tuple[Block, ...]:
    """One block per agent, keyed on the agent, excluding each excluded stem the pool holds."""

    blocks: list[Block] = []
    for definition in definitions:
        excluded = tuple(stem for stem in definition.excluded if stem in rules)
        if excluded:
            blocks.append(Block(f"agent {definition.name}", exclude=excluded))
    return tuple(blocks)
