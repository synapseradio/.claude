"""Read the skills of one rulesets directory: each `skills/<name>/SKILL.md` and what its frontmatter holds.

The reader records each fault it finds in a skill as data and words none of them. The faults
follow what Claude Code reads of a skill:
https://code.claude.com/docs/en/skills#frontmatter-reference
"""

from __future__ import annotations

import dataclasses
import pathlib
from typing import Literal

import yaml

from rulesets.documents import split_frontmatter
from rulesets.source.text_file import UnreadableFile, read_text_file

SKILLS_DIRECTORY = "skills"
SKILL_FILE = "SKILL.md"

# Claude Code keeps `~/.claude/skills/synced/` for skills it downloads from claude.ai and skips
# a skill authored under that name: https://code.claude.com/docs/en/skills#where-skills-live
RESERVED_SKILL_NAME = "synced"

type SkillFault = Literal[
    "no-skill-file",
    "unreadable",
    "no-frontmatter",
    "frontmatter-unparsable",
    "no-description",
    "name-differs",
    "reserved-name",
]


@dataclasses.dataclass(frozen=True)
class Skill:
    """One skill directory as read. `faults` is empty for a skill Claude Code reads in full.

    `declared_name` is the frontmatter's `name` where it holds a string, and `detail` the cause
    of an unreadable file.
    """

    name: str
    directory: pathlib.Path
    faults: tuple[SkillFault, ...]
    declared_name: str | None = None
    detail: str | None = None

    @property
    def file(self) -> pathlib.Path:
        return self.directory / SKILL_FILE


def _read_skill(directory: pathlib.Path) -> Skill:
    name = directory.name
    reserved: tuple[SkillFault, ...] = (
        ("reserved-name",) if name.casefold() == RESERVED_SKILL_NAME else ()
    )
    path = directory / SKILL_FILE
    if not path.is_file():
        return Skill(name, directory, (*reserved, "no-skill-file"))
    try:
        text = read_text_file(path)
    except UnreadableFile as failure:
        return Skill(name, directory, (*reserved, "unreadable"), detail=failure.cause)
    split = split_frontmatter(text)
    if split is None:
        return Skill(name, directory, (*reserved, "no-frontmatter"))
    try:
        fields = yaml.safe_load(split[0])
    except yaml.YAMLError:
        return Skill(name, directory, (*reserved, "frontmatter-unparsable"))
    if not isinstance(fields, dict):
        return Skill(name, directory, (*reserved, "frontmatter-unparsable"))
    faults = list(reserved)
    description = fields.get("description")
    if not isinstance(description, str) or not description.strip():
        faults.append("no-description")
    declared = fields.get("name")
    declared_name = declared if isinstance(declared, str) else None
    if "name" in fields and declared_name != name:
        faults.append("name-differs")
    return Skill(name, directory, tuple(faults), declared_name)


def read_skills(root: pathlib.Path) -> dict[str, Skill]:
    """Every directory under `skills/` of the rulesets directory at `root`, by name in sorted order.

    A file, and an entry whose name opens on `.`, is no skill and reads as nothing.
    """
    folder = root / SKILLS_DIRECTORY
    if not folder.is_dir():
        return {}
    return {
        entry.name: _read_skill(entry)
        for entry in sorted(folder.iterdir())
        if entry.is_dir() and not entry.name.startswith(".")
    }
