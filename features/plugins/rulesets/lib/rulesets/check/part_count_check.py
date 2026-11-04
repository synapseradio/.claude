"""Contexts whose rules need more parts than one delivery carries."""

from __future__ import annotations

import itertools

from rulesets.check.findings import CheckWarning, ContextSubject
from rulesets.compose.composition import compose
from rulesets.delivery.parts import MAX_PARTS, pack_parts
from rulesets.delivery.rule_bodies import bodies_of
from rulesets.facts.context import Facts, Kind
from rulesets.session.state import SessionState
from rulesets.source.condition import ConditionError, fact_tests, parse_condition
from rulesets.source.directory import Present, RulesetsDirectory

_KINDS: tuple[Kind, ...] = ("session", "delegate")


def check_part_count(directory: RulesetsDirectory) -> tuple[CheckWarning, ...]:
    """One warning for each context of the matrix whose rules divide into too many parts.

    The matrix crosses each declared model and the unclaimed model, each agent a condition
    names and no agent, each kind, and the flag sets none, each flag alone, and every flag.
    A manifest that is missing or does not parse declares nothing, so its matrix is the
    contexts that receive every rule.
    """

    match directory.manifest:
        case Present(manifest):
            models, flags_declared, items = manifest.models, manifest.flags, manifest.items
            where = manifest.path
        case _:
            models, flags_declared, items = (), (), ()
            where = directory.root / "manifest.yaml"
    agents: list[str | None] = [None]
    for item in items:
        try:
            tests = fact_tests(parse_condition(item.condition))
        except ConditionError:
            continue
        agents.extend(test.value for test in tests if test.fact == "agent")
    flag_sets = dict.fromkeys(
        frozenset(chosen) for chosen in ((), *((flag,) for flag in flags_declared), flags_declared)
    )
    warnings: list[CheckWarning] = []
    for model, agent, kind, flags in itertools.product(
        (*models, None), dict.fromkeys(agents), _KINDS, flag_sets
    ):
        facts = Facts(model, agent, kind, flags)
        parts = pack_parts(bodies_of(compose(directory, facts, SessionState()), directory.pool))
        if len(parts) > MAX_PARTS:
            warnings.append(
                CheckWarning(
                    "too-many-parts",
                    ContextSubject(facts),
                    where,
                    None,
                    f"the rules of this context divide into {len(parts)} parts, "
                    f"and a delivery carries {MAX_PARTS}",
                )
            )
    return tuple(warnings)
