"""Conflicts among blocks: two variants of one rule set at one position by blocks that can both apply."""

from __future__ import annotations

import dataclasses
import itertools
import pathlib
from collections.abc import Callable

from rulesets.check.findings import CheckError, ReferencesSubject, ReferenceSubject
from rulesets.compose.applying import AppliedList
from rulesets.compose.precedence import PositionBand, Statement, conflicts
from rulesets.compose.statements import statements
from rulesets.facts.kinds import block_rank
from rulesets.source.condition import (
    And,
    Condition,
    ConditionError,
    FactTest,
    evaluate_with,
    fact_tests,
    parse_condition,
)
from rulesets.source.directory import Present, RulesetsDirectory
from rulesets.source.expansion import Expander
from rulesets.source.manifest import WhenItem

# A context holds one value of each of these facts, so two tests of different values cannot both hold.
_SINGLE_VALUED = ("model", "agent", "kind", "session")


@dataclasses.dataclass(frozen=True)
class _Block:
    condition: Condition
    statements: tuple[Statement, ...]


def can_hold_together(first: Condition, second: Condition) -> bool:
    """Whether some context makes both conditions true, given that a context has one model,
    one agent, one kind, and one session."""

    both = And(first, second)
    tests = fact_tests(both)
    values = [sorted({t.value for t in tests if t.fact == fact}) for fact in _SINGLE_VALUED]
    flags = sorted({t.value for t in tests if t.fact == "flag"})
    for chosen in itertools.product(*([None, *each] for each in values)):
        picked = dict(zip(_SINGLE_VALUED, chosen, strict=True))
        for bits in itertools.product((False, True), repeat=len(flags)):
            set_flags = {flag for flag, bit in zip(flags, bits, strict=True) if bit}

            if evaluate_with(both, _holds_in(picked, set_flags)):
                return True
    return False


def _holds_in(picked: dict[str, str | None], set_flags: set[str]) -> Callable[[FactTest], bool]:
    def holds(test: FactTest) -> bool:
        if test.fact == "flag":
            return test.value in set_flags
        return picked[test.fact] == test.value

    return holds


def check_conflicts(directory: RulesetsDirectory) -> tuple[CheckError, ...]:
    """One error for each rule two blocks set to different variants at one position."""

    if not isinstance(directory.manifest, Present):
        return ()
    manifest = directory.manifest.manifest
    expander = Expander(manifest.spreadable(), directory.pool.variants_by_rule())
    blocks = [block for item in manifest.items if (block := _block(item, expander))]
    errors: list[CheckError] = []
    for first, second in itertools.combinations(blocks, 2):
        if not can_hold_together(first.condition, second.condition):
            continue
        by_rule: dict[str, list[Statement]] = {}
        for statement in (*first.statements, *second.statements):
            by_rule.setdefault(statement.rule, []).append(statement)
        for rule, about in by_rule.items():
            for conflict in conflicts(tuple(about)):
                setting = {id(statement) for statement in conflict.statements}
                if all(
                    any(id(s) in setting for s in block.statements) for block in (first, second)
                ):
                    errors.append(_error(manifest.path, rule, conflict.statements))
    return tuple(errors)


def _block(item: WhenItem, expander: Expander) -> _Block | None:
    try:
        condition = parse_condition(item.condition)
    except ConditionError:
        return None
    applied = AppliedList(PositionBand.DIRECTORY, block_rank(condition), item.references)
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
