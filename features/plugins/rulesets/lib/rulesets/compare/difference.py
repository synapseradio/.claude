"""The first rule at which what a source delivers and what the engine delivers part ways."""

from __future__ import annotations

import dataclasses
from collections.abc import Mapping

from rulesets.compare.delivered_text import DeliveredText


@dataclasses.dataclass(frozen=True)
class Difference:
    """`variant` is the one the engine delivers, else the one the source delivers; None is the default form."""

    rule: str
    variant: str | None
    reason: str

    def describe(self) -> str:
        where = f"variant {self.variant}" if self.variant else "its default form"
        return f"rule {self.rule} at {where}: {self.reason}"


def first_difference(
    source: Mapping[str, DeliveredText], engine: Mapping[str, DeliveredText]
) -> Difference | None:
    """The first rule by name that one side lacks or delivers other text for; the sequence is ignored."""

    for rule in sorted(source.keys() | engine.keys()):
        delivered, received = source.get(rule), engine.get(rule)
        if received is None and delivered is not None:
            return Difference(
                rule, delivered.variant, "the rulesets directory delivers no such rule"
            )
        if delivered is None and received is not None:
            return Difference(rule, received.variant, "the source delivers no such rule")
        if delivered is not None and received is not None and delivered.text != received.text:
            return Difference(rule, received.variant, "the text differs")
    return None
