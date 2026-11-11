"""One context's composed rules: which rules it receives, each at one variant."""

from __future__ import annotations

import dataclasses

from rulesets.compose.applying import SkippedBlock, applying_lists, skipped_blocks
from rulesets.compose.precedence import Included, Statement, VariantConflict, inclusion, variant
from rulesets.compose.skipped import SkippedReference, skipped_references
from rulesets.compose.statements import statements
from rulesets.compose.withheld import withheld
from rulesets.facts.context import Facts
from rulesets.session.state import SessionState
from rulesets.source.directory import Present, RulesetsDirectory
from rulesets.source.expansion import Expander


@dataclasses.dataclass(frozen=True)
class DeliveredRule:
    """A rule a context receives; `variant` is None for the default form."""

    rule: str
    variant: str | None


@dataclasses.dataclass(frozen=True)
class DeliveredConflict:
    """A conflict delivery fell back from, with the variant it delivered (None: the default form)."""

    rule: str
    variant: str | None
    conflict: VariantConflict


@dataclasses.dataclass(frozen=True)
class WithheldRule:
    """A rule the composition reached and delivery withholds, with the error that withholds it."""

    rule: str
    error: str


@dataclasses.dataclass(frozen=True)
class Composition:
    """The rules a context receives, sorted by name, each once, and what the composition met."""

    rules: tuple[DeliveredRule, ...]
    conflicts: tuple[DeliveredConflict, ...]
    skipped: tuple[SkippedReference, ...] = ()
    withheld: tuple[WithheldRule, ...] = ()
    skipped_blocks: tuple[SkippedBlock, ...] = ()


def expander_of(directory: RulesetsDirectory) -> Expander:
    match directory.config:
        case Present(config):
            lists = config.spreadable()
        case _:
            lists = {}
    return Expander(lists, directory.pool.variants_by_rule())


def context_statements(
    directory: RulesetsDirectory, facts: Facts, state: SessionState
) -> tuple[Statement, ...]:
    """Every statement the applying lists of a context make, about every rule."""

    return statements(applying_lists(directory, facts, state), expander_of(directory))


def compose(directory: RulesetsDirectory, facts: Facts, state: SessionState) -> Composition:
    """Compose the rules `facts` receives from the directory, with the session band in `state`."""

    expander = expander_of(directory)
    applied = applying_lists(directory, facts, state)
    made = statements(applied, expander)
    barred = withheld(directory.pool)
    by_rule: dict[str, list[Statement]] = {}
    for statement in made:
        by_rule.setdefault(statement.rule, []).append(statement)
    delivered: list[DeliveredRule] = []
    met: list[DeliveredConflict] = []
    held: list[WithheldRule] = []
    for rule, about in sorted(by_rule.items()):
        if not isinstance(inclusion(tuple(about)), Included):
            continue
        if rule in barred:
            held.append(WithheldRule(rule, barred[rule]))
            continue
        outcome = variant(tuple(about))
        delivered.append(DeliveredRule(rule, outcome.variant))
        if outcome.conflict is not None:
            met.append(DeliveredConflict(rule, outcome.variant, outcome.conflict))
    return Composition(
        tuple(delivered),
        tuple(met),
        skipped_references(applied, expander),
        tuple(held),
        skipped_blocks(directory),
    )
