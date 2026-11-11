"""Which lists apply in one context: `defaults`, each block whose key holds, and the session band's."""

from __future__ import annotations

import dataclasses
from collections.abc import Sequence

from rulesets.compose.origin import BlockOrigin, DefaultsOrigin, Origin, SessionBandOrigin
from rulesets.compose.precedence import PositionBand
from rulesets.facts.context import Facts
from rulesets.facts.kinds import Rank, block_rank
from rulesets.session.state import Band, SessionState
from rulesets.source.condition import ConditionError, Truth, evaluate, parse_condition
from rulesets.source.directory import Present, RulesetsDirectory
from rulesets.source.reference import Reference, parse_reference
from rulesets.source.undeclared import Undeclared, undeclared_names


@dataclasses.dataclass(frozen=True)
class AppliedList:
    band: PositionBand
    rank: Rank
    references: Sequence[Reference]
    origin: Origin


@dataclasses.dataclass(frozen=True)
class SkippedBlock:
    """A block whose condition names models or flags the config does not declare; it applies nowhere."""

    condition: str
    line: int
    undeclared: Undeclared


def skipped_blocks(directory: RulesetsDirectory) -> tuple[SkippedBlock, ...]:
    """The blocks delivery skips for naming an undeclared model or flag."""

    if not isinstance(directory.config, Present):
        return ()
    skipped: list[SkippedBlock] = []
    for block in directory.config.config.blocks:
        try:
            condition = parse_condition(block.condition)
        except ConditionError:
            continue
        undeclared = undeclared_names(condition, directory.config.config)
        if undeclared.named:
            skipped.append(SkippedBlock(block.condition, block.line, undeclared))
    return tuple(skipped)


_SPREAD_ALL = parse_reference("all.*", 0)
_REMOVE_ALL = parse_reference("all.*", 0, remove=True)


def applying_lists(
    directory: RulesetsDirectory, facts: Facts, state: SessionState
) -> tuple[AppliedList, ...]:
    """The applying lists in order: defaults, blocks in file order, then the session band's.

    A config that is missing or does not parse applies one list, the spread of every rule.
    """

    match directory.config:
        case Present(config):
            applied = [
                AppliedList(
                    PositionBand.DIRECTORY,
                    Rank.NONE,
                    config.defaults.references if config.defaults else (),
                    DefaultsOrigin(),
                )
            ]
            for block in config.blocks:
                try:
                    condition = parse_condition(block.condition)
                except ConditionError:
                    continue
                if undeclared_names(condition, config).named:
                    continue
                if evaluate(condition, facts) is Truth.TRUE:
                    applied.append(
                        AppliedList(
                            PositionBand.DIRECTORY,
                            block_rank(condition),
                            block.references,
                            BlockOrigin(block.condition),
                        )
                    )
        case _:
            applied = [
                AppliedList(PositionBand.DIRECTORY, Rank.NONE, (_SPREAD_ALL,), DefaultsOrigin())
            ]
    match state.band:
        case Band.ALL:
            applied.append(
                AppliedList(PositionBand.SESSION, Rank.NONE, (_SPREAD_ALL,), SessionBandOrigin())
            )
        case Band.NONE:
            applied.append(
                AppliedList(PositionBand.SESSION, Rank.NONE, (_REMOVE_ALL,), SessionBandOrigin())
            )
        case None:
            pass
    return tuple(applied)
