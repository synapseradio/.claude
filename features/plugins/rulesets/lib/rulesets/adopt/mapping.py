"""A tier corpus or rules folder mapped to the pool files, model names, and blocks of a rulesets directory."""

from __future__ import annotations

import dataclasses
import pathlib
from collections.abc import Mapping

from rulesets.adopt.rules_folder import RulesFolder
from rulesets.adopt.skipped import Skipped
from rulesets.adopt.source import Source
from rulesets.adopt.tier_corpus import TierCorpus, delivered_stems

_MODEL_PREFIX = "claude-"


@dataclasses.dataclass(frozen=True)
class Block:
    """A `when` item: a condition and the references of its list."""

    condition: str
    entries: tuple[str, ...]


@dataclasses.dataclass(frozen=True)
class AdoptedDirectory:
    """What adopt writes: pool file names with the source file each copies, model names, and blocks."""

    pool: Mapping[str, pathlib.Path]
    models: tuple[str, ...]
    blocks: tuple[Block, ...]
    skipped: tuple[Skipped, ...]

    def rule_names(self) -> frozenset[str]:
        return frozenset(name.removesuffix(".md").partition("@")[0] for name in self.pool)


def model_name(tier: str) -> str:
    """The model name a tier declares: the tier name without its `claude-` prefix."""

    return tier.removeprefix(_MODEL_PREFIX)


def map_corpus(corpus: TierCorpus) -> AdoptedDirectory:
    """`default/` becomes the default forms; each other tier's files become variants its model's block adds.

    A tier's stems to leave out become removes in that block.
    """

    pool = {f"{stem}.md": path for stem, path in corpus.default.items()}
    default_stems = tuple(sorted(corpus.default))
    blocks: list[Block] = []
    for tier in corpus.tiers.values():
        kept = delivered_stems(tier.entry, default_stems)
        removes = tuple(f"-{stem}" for stem in default_stems if stem not in kept)
        adds: list[str] = []
        for stem, path in sorted(tier.files.items()):
            if stem in kept:
                pool[f"{stem}@{tier.name}.md"] = path
                adds.append(f"{stem}@{tier.name}")
        if removes or adds:
            blocks.append(Block(f"model {model_name(tier.name)}", (*removes, *adds)))
    tiers = (*corpus.prefixes, *corpus.tiers)
    models = tuple(dict.fromkeys(model_name(tier) for tier in tiers))
    return AdoptedDirectory(pool, models, tuple(blocks), corpus.skipped)


def map_rules_folder(folder: RulesFolder) -> AdoptedDirectory:
    return AdoptedDirectory(
        {f"{stem}.md": path for stem, path in folder.rules.items()}, (), (), folder.skipped
    )


def map_source(source: Source) -> AdoptedDirectory:
    match source:
        case TierCorpus():
            return map_corpus(source)
        case RulesFolder():
            return map_rules_folder(source)
