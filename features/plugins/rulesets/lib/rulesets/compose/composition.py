"""One context's composed rules: which rules it receives, each at one variant."""

from __future__ import annotations

import dataclasses

from rulesets.compose.applying import applying_lists
from rulesets.compose.precedence import Included, Statement, VariantConflict, inclusion, variant
from rulesets.compose.statements import statements
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
class Composition:
    """The rules a context receives, sorted by name, each once, and the conflicts met."""

    rules: tuple[DeliveredRule, ...]
    conflicts: tuple[DeliveredConflict, ...]


def compose(directory: RulesetsDirectory, facts: Facts, state: SessionState) -> Composition:
    """Compose the rules `facts` receives from the directory, with the session band in `state`."""

    match directory.manifest:
        case Present(manifest):
            lists = manifest.spreadable()
        case _:
            lists = {}
    expander = Expander(lists, directory.pool.variants_by_rule())
    made = statements(applying_lists(directory, facts, state), expander)
    by_rule: dict[str, list[Statement]] = {}
    for statement in made:
        by_rule.setdefault(statement.rule, []).append(statement)
    delivered: list[DeliveredRule] = []
    met: list[DeliveredConflict] = []
    for rule, about in sorted(by_rule.items()):
        if not isinstance(inclusion(tuple(about)), Included):
            continue
        outcome = variant(tuple(about))
        delivered.append(DeliveredRule(rule, outcome.variant))
        if outcome.conflict is not None:
            met.append(DeliveredConflict(rule, outcome.variant, outcome.conflict))
    return Composition(tuple(delivered), tuple(met))
