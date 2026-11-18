"""What the skills of a rulesets directory and the config's pairings carry: errors in each, and pointer warnings.

A pairing makes a rule the pointer to a skill that holds its body. This module words the faults
`rulesets.source.skills` records, the pairings that name a missing rule or skill, and a paired rule
file whose text never names its skill.
"""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from typing import assert_never

from rulesets.check.findings import (
    CheckError,
    CheckWarning,
    ErrorKind,
    PairingSubject,
    RuleSubject,
    SkillSubject,
)
from rulesets.source.config import Config, Pairing
from rulesets.source.pool import Pool
from rulesets.source.skills import SKILL_FILE, SKILLS_DIRECTORY, Skill, SkillFault


def skill_errors(skills: Mapping[str, Skill]) -> tuple[CheckError, ...]:
    """Every fault of every skill, skill by skill in name order."""
    return tuple(_fault_error(skill, fault) for skill in skills.values() for fault in skill.faults)


def _fault_error(skill: Skill, fault: SkillFault) -> CheckError:
    kind: ErrorKind
    match fault:
        case "no-skill-file":
            kind, line = "skill-file", None
            message = (
                f"`{SKILLS_DIRECTORY}/{skill.name}/` holds no `{SKILL_FILE}`, so no skill loads"
            )
        case "unreadable":
            kind, line, message = "skill-file", None, skill.detail or "the file cannot be read"
        case "no-frontmatter":
            kind, line = "skill-frontmatter", 1
            message = (
                f"`{SKILL_FILE}` opens on no `---` frontmatter block, so the skill carries no "
                "description to load it by"
            )
        case "frontmatter-unparsable":
            kind, line = "skill-frontmatter", 1
            message = "the frontmatter is not a YAML mapping, so the skill loads with no fields set"
        case "no-description":
            kind, line = "skill-frontmatter", 1
            message = "the frontmatter holds no `description`, which says when the skill loads"
        case "name-differs":
            kind, line = "skill-name", 1
            message = (
                f"the frontmatter's `name` is `{skill.declared_name}`, and a pairing names a "
                f"skill by its directory, `{skill.name}`; give both one name"
            )
        case "reserved-name":
            kind, line = "skill-name", None
            message = (
                f"Claude Code keeps `{skill.name}` for skills synced from claude.ai and skips "
                "a skill authored under it; rename the directory"
            )
        case _:
            assert_never(fault)
    return CheckError(kind, SkillSubject(skill.name), skill.file, line, message)


def pairing_errors(
    config: Config, pool: Pool, skills: Mapping[str, Skill]
) -> tuple[CheckError, ...]:
    """An error for each pairing whose rule the pool lacks, and for each whose skill is missing."""
    return tuple(_pairing_errors(config, pool, skills))


def _pairing_errors(
    config: Config, pool: Pool, skills: Mapping[str, Skill]
) -> Iterator[CheckError]:
    for pairing in config.pairings:
        subject = PairingSubject(pairing.rule)
        if pairing.rule not in pool.rules:
            yield CheckError(
                "pairing-unknown-rule",
                subject,
                config.path,
                pairing.line,
                f"the pool holds no rule `{pairing.rule}`",
            )
        if pairing.skill not in skills:
            yield CheckError(
                "pairing-unknown-skill",
                subject,
                config.path,
                pairing.line,
                f"no skill `{pairing.skill}` stands at "
                f"`{SKILLS_DIRECTORY}/{pairing.skill}/{SKILL_FILE}`",
            )


def pointer_warnings(config: Config, pool: Pool) -> tuple[CheckWarning, ...]:
    """A warning for each file of a paired rule whose text never names its skill in backticks."""
    return tuple(_pointer_warnings(config.pairings, pool))


def _pointer_warnings(pairings: tuple[Pairing, ...], pool: Pool) -> Iterator[CheckWarning]:
    for pairing in pairings:
        rule = pool.rules.get(pairing.rule)
        if rule is None:
            continue
        named = f"`{pairing.skill}`"
        for file in rule.files():
            if file.problem is None and named not in file.text:
                yield CheckWarning(
                    "pointer-unnamed",
                    RuleSubject(rule.name),
                    file.path,
                    None,
                    f"`{file.path.name}` is paired with skill `{pairing.skill}`, and its text "
                    f"never names {named}, so a reader of the rule cannot find the skill",
                )
