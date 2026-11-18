"""Link each skill of a rulesets directory into the personal skills folder, where Claude Code finds it by name.

Claude Code loads a personal skill from `~/.claude/skills/<name>/SKILL.md`, follows a `<name>`
entry there that is a symlink to a directory elsewhere, and picks up an added or removed entry
within the running session: https://code.claude.com/docs/en/skills#where-skills-live and
https://code.claude.com/docs/en/skills#live-change-detection

A link this module writes is relative, so it holds no account name. It owns only the links that
point into the rulesets directory's `skills/`, and leaves every other entry as it stands.
"""

from __future__ import annotations

import dataclasses
import json
import os
import pathlib
from collections.abc import Mapping, Sequence
from typing import Literal

from rulesets.locations import Locations
from rulesets.record_entry import HookResult
from rulesets.source.skills import SKILLS_DIRECTORY, read_skills

PERSONAL_SKILLS_DIRECTORY = "skills"

type LinkState = Literal["linked", "missing", "stale", "blocked"]


@dataclasses.dataclass(frozen=True)
class SkillLink:
    """One entry of the personal skills folder and its state against the rulesets directory.

    `linked`: the entry links to the skill. `missing`: no entry stands for a skill. `stale`: the
    entry links into the rulesets directory's `skills/` at a skill no longer there. `blocked`:
    another file, folder, or link stands where a skill's link goes.
    """

    name: str
    link: pathlib.Path
    target: pathlib.Path
    state: LinkState

    def line(self, *, written: bool) -> str:
        match self.state:
            case "linked":
                return f"{self.name}: linked, {self.link} -> {self.target}"
            case "missing":
                verb = "linked" if written else "unlinked; --link links"
                return f"{self.name}: {verb}, {self.link} -> {self.target}"
            case "stale":
                verb = "removed" if written else "stale; --link removes"
                return f"{self.name}: {verb}, {self.link} links to a skill no longer there"
            case "blocked":
                return (
                    f"{self.name}: blocked, {self.link} is not a link to {self.target}; "
                    "move it aside, then link again"
                )


def _points_at(link: pathlib.Path, target: pathlib.Path) -> bool:
    return link.is_symlink() and link.resolve() == target.resolve()


def _inside(path: pathlib.Path, folder: pathlib.Path) -> bool:
    return path.is_relative_to(folder.resolve())


def skill_links(root: pathlib.Path, personal: pathlib.Path) -> tuple[SkillLink, ...]:
    """The state of each skill's link in `personal`, then each stale link, each by name in sorted order."""
    root = root.resolve()
    folder = root / SKILLS_DIRECTORY
    links: list[SkillLink] = []
    skills = read_skills(root)
    for name, skill in skills.items():
        link = personal / name
        if _points_at(link, skill.directory):
            state: LinkState = "linked"
        elif link.is_symlink() or link.exists():
            state = "blocked"
        else:
            state = "missing"
        links.append(SkillLink(name, link, skill.directory, state))
    if personal.is_dir() and folder.is_dir():
        for entry in sorted(personal.iterdir()):
            if entry.name in skills or not entry.is_symlink():
                continue
            target = entry.resolve()
            if _inside(target, folder) and not target.exists():
                links.append(SkillLink(entry.name, entry, target, "stale"))
    return tuple(links)


def write_links(links: Sequence[SkillLink]) -> None:
    """Create each missing link as a relative symlink, and remove each stale one."""
    for link in links:
        match link.state:
            case "missing":
                link.link.parent.mkdir(parents=True, exist_ok=True)
                relative = os.path.relpath(link.target, link.link.parent.resolve())
                link.link.symlink_to(relative, target_is_directory=True)
            case "stale":
                link.link.unlink()
            case "linked" | "blocked":
                pass


def personal_skills(locations: Locations) -> pathlib.Path:
    return locations.config / PERSONAL_SKILLS_DIRECTORY


def link_at_session_start(
    argv: Sequence[str], stdin: bytes, environ: Mapping[str, str]
) -> HookResult:
    """Link the configured rulesets directory's skills; say only what blocks a link.

    The harness shows a `systemMessage` to the person and keeps it out of the agent's context:
    https://code.claude.com/docs/en/hooks#json-output
    """
    del argv, stdin
    locations = Locations.from_environment(environ)
    try:
        links = skill_links(locations.rulesets, personal_skills(locations))
        write_links(links)
    except OSError as failure:
        notes = [f"rulesets could not link its skills: {failure}"]
    else:
        notes = [link.line(written=True) for link in links if link.state == "blocked"]
    if not notes:
        return HookResult(0, "", "")
    return HookResult(0, json.dumps({"systemMessage": "\n".join(notes)}) + "\n", "")
