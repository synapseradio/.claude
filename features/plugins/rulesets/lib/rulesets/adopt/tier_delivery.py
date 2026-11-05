"""What a tier corpus or rules folder delivers to one context, read without the engine."""

from __future__ import annotations

from collections.abc import Collection

from rulesets.adopt.opening_marker import under_delivery_marker
from rulesets.adopt.rules_folder import RulesFolder
from rulesets.adopt.source import Source
from rulesets.adopt.tier_corpus import Tier, TierCorpus, delivered_stems
from rulesets.compare.delivered_text import DeliveredText


def tier_for(corpus: TierCorpus, identifier: str | None) -> Tier | None:
    """The tier a model identifier reads, or None for `default`.

    A tier named for the identifier wins; else the tier of the longest prefix the prefix map
    holds that the identifier opens on; else `default`.
    """

    if identifier is None:
        return None
    if identifier in corpus.tiers:
        return corpus.tiers[identifier]
    matches = [
        (len(prefix), tier)
        for tier, prefixes in corpus.prefixes.items()
        for prefix in prefixes
        if tier in corpus.tiers and identifier.startswith(prefix)
    ]
    return corpus.tiers[max(matches, key=lambda match: match[0])[1]] if matches else None


def source_rules(
    source: Source, identifier: str | None, excluded: Collection[str]
) -> dict[str, DeliveredText]:
    """The bytes of each rule the source delivers on `identifier`, less the stems an agent excludes.

    A rules folder delivers every file to every context and knows no exclusions; its files carry
    no marker, so they stand under the marker delivery would write. A tier corpus's files are
    delivered as they are, marker included.
    """

    match source:
        case RulesFolder(rules):
            return {
                stem: DeliveredText(under_delivery_marker(stem, path.read_bytes()), None)
                for stem, path in rules.items()
            }
        case TierCorpus(default=default):
            tier = tier_for(source, identifier)
            stems = delivered_stems(tier.entry, default) if tier else tuple(sorted(default))
            found: dict[str, DeliveredText] = {}
            for stem in stems:
                if stem in excluded:
                    continue
                if tier and stem in tier.files:
                    found[stem] = DeliveredText(tier.files[stem].read_bytes(), tier.name)
                else:
                    found[stem] = DeliveredText(default[stem].read_bytes(), None)
            return found
