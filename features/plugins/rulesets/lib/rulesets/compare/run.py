"""The comparison: what a source delivers against what a rulesets directory delivers, per context."""

from __future__ import annotations

import dataclasses
import pathlib
from collections.abc import Collection

from rulesets.adopt.agent_exclusions import read_definitions
from rulesets.adopt.source import read_source
from rulesets.adopt.tier_corpus import TierCorpus
from rulesets.adopt.tier_delivery import source_rules
from rulesets.compare.difference import Difference, first_difference
from rulesets.compare.engine_delivery import engine_rules
from rulesets.compare.matrix import ContextKey, matrix
from rulesets.compare.recorded_models import recorded_identifiers
from rulesets.locations import Locations
from rulesets.source.directory import read_directory


@dataclasses.dataclass(frozen=True)
class ContextResult:
    """One context's outcome; `expected` is set where `--expect` named its identifier."""

    context: ContextKey
    difference: Difference | None
    expected: bool


@dataclasses.dataclass(frozen=True)
class CompareReport:
    results: tuple[ContextResult, ...]

    @property
    def failed(self) -> bool:
        """Whether any context differs outside the identifiers `--expect` named."""

        return any(r.difference and not r.expected for r in self.results)

    def lines(self) -> list[str]:
        shown = [
            f"{'expected' if r.expected else 'different'}: {r.context}: {r.difference.describe()}"
            for r in self.results
            if r.difference
        ]
        count = len(self.results)
        return [*shown, f"compared {count} contexts"]


def compare(
    source: pathlib.Path,
    directory: pathlib.Path,
    expect: Collection[str],
    locations: Locations,
) -> CompareReport:
    """Compare every context of the matrix. Raises SourceError where `source` cannot be read.

    The matrix crosses the identifiers the delivery records name, the tiers the source names,
    the context with no model, and each identifier in `expect`, with each agent definition and
    with no agent.
    """

    read = read_source(source)
    engine = read_directory(directory)
    definitions = read_definitions(locations.config / "agents")
    excluded = {definition.name: frozenset(definition.excluded) for definition in definitions}
    tiers = tuple(read.tiers) if isinstance(read, TierCorpus) else ()
    identifiers = (None, *tiers, *recorded_identifiers(locations), *expect)
    results = []
    for context in matrix(identifiers, definitions):
        difference = first_difference(
            source_rules(read, context.identifier, excluded.get(context.agent or "", frozenset())),
            engine_rules(engine, context),
        )
        results.append(ContextResult(context, difference, context.identifier in expect))
    return CompareReport(tuple(results))
