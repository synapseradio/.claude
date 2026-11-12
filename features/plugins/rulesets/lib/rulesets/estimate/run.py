"""Each context's composed size and estimated tokens, with the change since a snapshot."""

from __future__ import annotations

import dataclasses
import pathlib

from rulesets.compose.composition import Composition, DeliveredRule, compose
from rulesets.context_matrix import NONE, Context, contexts
from rulesets.estimate.figures import estimated_tokens, figure_for
from rulesets.facts.named_context import named_context
from rulesets.render.context_render import render_context
from rulesets.session.state import SessionState
from rulesets.source.directory import Present, RulesetsDirectory, read_directory

_SOURCE = "source"
_COMPOSITIONS = "compositions.txt"

type Baseline = dict[str, int]


@dataclasses.dataclass(frozen=True)
class Row:
    """One context's size. `before` is the baseline's token estimate, None where it has no such context."""

    context: str
    model: str
    characters: int
    words: int
    tokens: int
    before: int | None
    defaulted: bool

    @property
    def delta(self) -> int | None:
        return None if self.before is None else self.tokens - self.before


def composed_text(directory: RulesetsDirectory, context: Context) -> str:
    """The text `render --out` writes for the context."""
    config = directory.config.config if isinstance(directory.config, Present) else None
    facts = named_context(
        context.model,
        context.agent,
        context.kind,
        [context.tool] if context.tool else [],
        [context.flag] if context.flag else [],
        config,
    )
    return render_context(compose(directory, facts, SessionState()), directory.pool)


def read_baseline(snapshot: pathlib.Path) -> Baseline | None:
    """The characters of each context's composed text a snapshot recorded, by context name.

    None where `snapshot` is no snapshot. The text is each recorded rule read from the
    snapshot's own copy of the pool.
    """
    recorded = snapshot / _COMPOSITIONS
    if not (snapshot / _SOURCE).is_dir() or not recorded.is_file():
        return None
    pool = read_directory(snapshot / _SOURCE).pool
    sizes: Baseline = {}
    for line in recorded.read_text(encoding="utf-8").splitlines():
        label, _, listed = line.partition("\t")
        rules = tuple(_delivered(form) for form in listed.split() if form != NONE)
        sizes[label] = len(render_context(Composition(rules, ()), pool))
    return sizes


def _delivered(form: str) -> DeliveredRule:
    rule, _, variant = form.partition("@")
    return DeliveredRule(rule, variant or None)


def rows(directory: RulesetsDirectory, baseline: Baseline | None) -> list[Row]:
    found: list[Row] = []
    for context in contexts(directory):
        text = composed_text(directory, context)
        figure, defaulted = figure_for(context.model)
        recorded = None if baseline is None else baseline.get(context.label())
        found.append(
            Row(
                context.label(),
                context.model or NONE,
                len(text),
                len(text.split()),
                estimated_tokens(len(text), figure),
                None if recorded is None else estimated_tokens(recorded, figure),
                defaulted,
            )
        )
    return found


def _signed(delta: int | None) -> str:
    if delta is None:
        return NONE
    return "0" if delta == 0 else f"{delta:+d}"


def table(found: list[Row], with_baseline: bool) -> list[str]:
    """A header line and one line per row, columns right-aligned and set two spaces apart."""
    header = ["context", "model", "chars", "words", "tokens"]
    if with_baseline:
        header += ["before", "delta"]
    header.append("figure")
    body = []
    for row in found:
        cells = [row.context, row.model, str(row.characters), str(row.words), str(row.tokens)]
        if with_baseline:
            cells += [NONE if row.before is None else str(row.before), _signed(row.delta)]
        body.append([*cells, "default" if row.defaulted else "table"])
    widths = [max(len(line[column]) for line in [header, *body]) for column in range(len(header))]
    numeric = range(2, len(header) - 1)
    return [
        "  ".join(
            cell.rjust(width) if column in numeric else cell.ljust(width)
            for column, (cell, width) in enumerate(zip(line, widths, strict=True))
        ).rstrip()
        for line in [header, *body]
    ]
