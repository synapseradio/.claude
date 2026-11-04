"""Contexts whose rules need more parts than one delivery carries."""

from __future__ import annotations

import itertools

from rulesets.check.findings import CheckWarning, ContextSubject
from rulesets.compose.composition import compose
from rulesets.delivery.parts import MAX_PARTS, bodies_of, pack_parts
from rulesets.facts.context import Facts, Kind
from rulesets.session.state import SessionState
from rulesets.source.condition import ConditionError, fact_tests, parse_condition
from rulesets.source.directory import Present, RulesetsDirectory

_KINDS: tuple[Kind, ...] = ("session", "delegate")


def check_part_count(directory: RulesetsDirectory) -> tuple[CheckWarning, ...]:
    """One warning for each context of the matrix whose rules divide into too many parts.

    The matrix crosses each declared model (or none declared), each agent a condition names
    and no agent, each kind, and the flag sets none, each flag alone, and every flag.
    """

    if not isinstance(directory.manifest, Present):
        return ()
    manifest = directory.manifest.manifest
    agents: list[str | None] = [None]
    for item in manifest.items:
        try:
            tests = fact_tests(parse_condition(item.condition))
        except ConditionError:
            continue
        agents.extend(test.value for test in tests if test.fact == "agent")
    flag_sets = dict.fromkeys(
        frozenset(chosen) for chosen in ((), *((flag,) for flag in manifest.flags), manifest.flags)
    )
    warnings: list[CheckWarning] = []
    for model, agent, kind, flags in itertools.product(
        manifest.models or (None,), dict.fromkeys(agents), _KINDS, flag_sets
    ):
        facts = Facts(model, agent, kind, flags)
        parts = pack_parts(bodies_of(compose(directory, facts, SessionState()), directory.pool))
        if len(parts) > MAX_PARTS:
            warnings.append(
                CheckWarning(
                    "too-many-parts",
                    ContextSubject(facts),
                    manifest.path,
                    None,
                    f"the rules of this context divide into {len(parts)} parts, "
                    f"and a delivery carries {MAX_PARTS}",
                )
            )
    return tuple(warnings)
