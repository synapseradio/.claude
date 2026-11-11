"""Conflicts among blocks: two variants of one rule set at one position by blocks that can both apply."""

from __future__ import annotations

import dataclasses
import itertools
import pathlib

from rulesets.check.findings import CheckError, ReferencesSubject, ReferenceSubject
from rulesets.compose.applying import AppliedList
from rulesets.compose.origin import BlockOrigin
from rulesets.compose.precedence import (
    Adds,
    PositionBand,
    Statement,
    Strikes,
    VariantConflict,
    conflicts,
)
from rulesets.compose.statements import statements
from rulesets.facts.kinds import block_rank
from rulesets.source.condition import And, Condition, ConditionError, Not, parse_condition
from rulesets.source.config import Block
from rulesets.source.directory import Present, RulesetsDirectory
from rulesets.source.expansion import Expander
from rulesets.source.satisfiability import can_hold


@dataclasses.dataclass(frozen=True)
class _Block:
    condition: Condition
    statements: tuple[Statement, ...]


def check_conflicts(directory: RulesetsDirectory) -> tuple[CheckError, ...]:
    """One error for each rule two blocks set to different variants at one position."""

    if not isinstance(directory.config, Present):
        return ()
    config = directory.config.config
    expander = Expander(config.spreadable(), directory.pool.variants_by_rule())
    blocks = [block for written in config.blocks if (block := _block(written, expander))]
    errors: list[CheckError] = []
    for first, second in itertools.combinations(blocks, 2):
        if not can_hold(And(first.condition, second.condition)):
            continue
        by_rule: dict[str, list[Statement]] = {}
        for statement in (*first.statements, *second.statements):
            by_rule.setdefault(statement.rule, []).append(statement)
        others = [block for block in blocks if block is not first and block is not second]
        for rule, about in by_rule.items():
            for conflict in conflicts(tuple(about)):
                setting = {id(statement) for statement in conflict.statements}
                if all(
                    any(id(s) in setting for s in block.statements) for block in (first, second)
                ) and _stands_in_some_context(first, second, others, conflict):
                    errors.append(_error(config.path, rule, conflict.statements))
    return tuple(errors)


def _stands_in_some_context(
    first: _Block, second: _Block, others: list[_Block], conflict: VariantConflict
) -> bool:
    """Whether some context holds both blocks and no other block strikes a conflicting variant.

    A strike at the conflict's position or above removes its variant from the position's sets.
    """

    variants = {s.says.variant for s in conflict.statements if isinstance(s.says, Adds)}
    wanted: Condition = And(first.condition, second.condition)
    for block in others:
        strikes = any(
            isinstance(s.says, Strikes)
            and s.rule == conflict.rule
            and s.says.variant in variants
            and s.position >= conflict.position
            for s in block.statements
        )
        if strikes:
            wanted = And(wanted, Not(block.condition))
    return can_hold(wanted)


def _block(written: Block, expander: Expander) -> _Block | None:
    try:
        condition = parse_condition(written.condition)
    except ConditionError:
        return None
    applied = AppliedList(
        PositionBand.DIRECTORY,
        block_rank(condition),
        written.references,
        BlockOrigin(written.condition),
    )
    return _Block(condition, statements((applied,), expander))


def _error(path: pathlib.Path, rule: str, setting: tuple[Statement, ...]) -> CheckError:
    members = tuple(dict.fromkeys(ReferenceSubject(s.source.text, s.source.line) for s in setting))
    names = " and ".join(f"`{member.text}`" for member in members)
    return CheckError(
        "variant-conflict",
        ReferencesSubject(members),
        path,
        members[0].line,
        f"blocks set rule `{rule}` to different variants at one position: {names}",
    )
