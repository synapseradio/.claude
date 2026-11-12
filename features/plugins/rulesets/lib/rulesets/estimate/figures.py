"""Characters per token and the tokenizer multiplier for each model name a config declares.

The figures live in `figures.json`, each value beside the page that states it. A figure
estimates tokens for English prose. Exact counts come from
https://platform.claude.com/docs/en/build-with-claude/token-counting.
"""

from __future__ import annotations

import dataclasses
import json
import pathlib


@dataclasses.dataclass(frozen=True)
class Figure:
    """Tokens for a text are its characters over `chars_per_token`, times `multiplier`.

    `chars_per_token` is the rate of the tokenizer before Claude 4.7; `multiplier` is how many
    times as many tokens a newer tokenizer produces for the same text.
    """

    chars_per_token: float
    chars_source: str
    multiplier: float
    multiplier_source: str


def _loaded() -> tuple[dict[str, Figure], Figure]:
    # https://platform.claude.com/docs/en/about-claude/glossary.md states both values in one
    # sentence for Claude 4.7 and later; it names no figure that tells the families apart, so
    # each table entry carries the same one. A model name the table lacks takes the default,
    # which is that same figure.
    data = json.loads(pathlib.Path(__file__).with_name("figures.json").read_text(encoding="utf-8"))
    return (
        {name: Figure(**fields) for name, fields in data["models"].items()},
        Figure(**data["default"]),
    )


FIGURES, DEFAULT = _loaded()


def figure_for(model: str | None) -> tuple[Figure, bool]:
    """The figure for a declared model name, and whether the table lacked it so the default stands."""
    if model is not None and model in FIGURES:
        return FIGURES[model], False
    return DEFAULT, True


def estimated_tokens(characters: int, figure: Figure) -> int:
    return round(characters / figure.chars_per_token * figure.multiplier)
