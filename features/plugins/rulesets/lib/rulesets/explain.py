"""One rule traced through one context: the lines that decided its inclusion and its variant."""

from __future__ import annotations

import dataclasses
from collections.abc import Mapping

from rulesets.compose.composition import context_statements, expander_of
from rulesets.compose.origin import BlockOrigin, DefaultsOrigin, SessionBandOrigin
from rulesets.compose.precedence import (
    Adds,
    Excluded,
    Included,
    Inclusion,
    Reach,
    Statement,
    Strikes,
    VariantOutcome,
    inclusion,
    inclusion_statements,
    variant,
)
from rulesets.compose.withheld import withheld
from rulesets.facts.context import AllToolsBut, Facts, ListedTools, NoClaim
from rulesets.session.state import SessionState
from rulesets.source.config import CONFIG_FILE
from rulesets.source.directory import Present, RulesetsDirectory
from rulesets.source.reference import SpreadTarget

_NO_CONFIG = "no config"


@dataclasses.dataclass(frozen=True)
class UnknownRule:
    """A name the pool holds no rule by."""

    rule: str


@dataclasses.dataclass(frozen=True)
class Explanation:
    """What decided one rule in one context.

    Each row list opens with the winning line, then holds the lines it beat from losing to
    winning. `variant_rows` is the variant's lines with the winner, where one stands, first.
    """

    rule: str
    facts: Facts
    config_file: str
    inclusion: Inclusion
    inclusion_rows: tuple[Statement, ...]
    variant: VariantOutcome
    variant_rows: tuple[Statement, ...]
    withheld: str | None
    routes: Mapping[Statement, tuple[str, ...]]


def _opening_with(winner: Statement | None, rows: list[Statement]) -> tuple[Statement, ...]:
    if winner is None:
        return tuple(rows)
    return (winner, *(row for row in rows if row is not winner))


def explain(directory: RulesetsDirectory, rule: str, facts: Facts) -> Explanation | UnknownRule:
    """Trace `rule` through the context `facts` names, with no session state."""

    if rule not in directory.pool.rules:
        return UnknownRule(rule)
    about = tuple(s for s in context_statements(directory, facts, SessionState()) if s.rule == rule)
    ascending = inclusion_statements(about)
    outcome = variant(about)
    setting = sorted(
        (
            s
            for s in about
            if isinstance(s.says, Strikes) or (isinstance(s.says, Adds) and s.says.variant)
        ),
        key=lambda s: s.position,
    )
    expander = expander_of(directory)
    routes = {
        s: expander.route_to(s.source.target.ruleset, rule)
        for s in about
        if isinstance(s.source.target, SpreadTarget)
    }
    config_file = (
        str(directory.config.config.path)
        if isinstance(directory.config, Present)
        else str(directory.root / CONFIG_FILE)
    )
    return Explanation(
        rule,
        facts,
        config_file,
        inclusion(about),
        ascending[-1:] + ascending[:-1],
        outcome,
        _opening_with(outcome.winner, setting),
        withheld(directory.pool).get(rule),
        routes,
    )


def _context_words(facts: Facts) -> str:
    named: list[str] = []
    match facts.model:
        case str() as name:
            named.append(f"model {name}")
        case NoClaim():
            named.append("model claimed by no declared name")
        case _:
            pass
    if isinstance(facts.agent, str):
        named.append(f"agent {facts.agent}")
    if isinstance(facts.kind, str):
        named.append(f"kind {facts.kind}")
    match facts.tools:
        case ListedTools(tools):
            named.append("tools " + ", ".join(sorted(tools)))
        case AllToolsBut():
            named.append("every tool but some")
        case _:
            pass
    named.extend(f"flag {flag}" for flag in sorted(facts.flags))
    return ", ".join(named) or "no fact named"


def _cells(label: str, statement: Statement, explanation: Explanation) -> tuple[str, ...]:
    line = statement.source.line
    location = f"{explanation.config_file}:{line}" if line else _NO_CONFIG
    match statement.origin:
        case DefaultsOrigin():
            key = "defaults"
        case BlockOrigin(condition):
            key = condition
        case SessionBandOrigin():
            key = "session toggle"
    if statement.position.reach is Reach.NAMED:
        reach = "names the rule"
    else:
        reach = f"through ruleset {' > '.join(explanation.routes[statement])}"
    return (label, location, key, statement.source.quoted, reach)


def _variant_label(row: Statement, explanation: Explanation) -> str:
    """What a line of the variant attribute did: won, conflicted, struck, struck a variant, or lost."""

    outcome = explanation.variant
    if row is outcome.winner:
        return "wins"
    if outcome.conflict and row in outcome.conflict.statements:
        return "conflict"
    if isinstance(row.says, Strikes):
        return "strikes"
    if isinstance(row.says, Adds) and any(
        isinstance(other.says, Strikes)
        and other.says.variant == row.says.variant
        and other.position >= row.position
        for other in explanation.variant_rows
    ):
        return "struck"
    return "beat" if outcome.winner else "line"


def _table(rows: list[tuple[str, ...]]) -> list[str]:
    widths = [max(len(row[column]) for row in rows) for column in range(len(rows[0]))]
    return [
        "  "
        + "  ".join(cell.ljust(width) for cell, width in zip(row, widths, strict=True)).rstrip()
        for row in rows
    ]


def format_explanation(explanation: Explanation) -> list[str]:
    """The printed lines: the rule and context, then inclusion, then variant, then any withholding."""

    outcome = explanation.variant
    on = isinstance(explanation.inclusion, Included)
    lines = [f"rule {explanation.rule}    context: {_context_words(explanation.facts)}"]

    match explanation.inclusion:
        case Included():
            lines.append("inclusion: on")
        case Excluded():
            lines.append("inclusion: off")
        case _:
            lines.append("inclusion: no list reaches the rule in this context")
    rows = [
        _cells("wins" if row is explanation.inclusion_rows[0] else "beat", row, explanation)
        for row in explanation.inclusion_rows
    ]
    lines.extend(_table(rows) if rows else [])

    if outcome.variant is not None:
        lines.append(f"variant: {outcome.variant}")
    elif on and explanation.withheld is None:
        lines.append("variant: none set; the default form is delivered")
    else:
        lines.append("variant: none set")
    rows = [
        _cells(_variant_label(row, explanation), row, explanation)
        for row in explanation.variant_rows
    ]
    lines.extend(_table(rows) if rows else [])
    if outcome.conflict is not None:
        names = " and ".join(f"`{s.source.text}`" for s in outcome.conflict.statements)
        taken = outcome.variant or "the default form"
        lines.append(
            f"  conflict: {names} set different variants at one position; delivery takes {taken}"
        )

    if explanation.withheld is not None:
        lines.append(
            f"withheld: `{explanation.rule}` is withheld at delivery: {explanation.withheld}"
        )
    return lines
