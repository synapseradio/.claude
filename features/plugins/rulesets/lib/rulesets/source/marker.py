"""The rule marker comment: written before a rule's text in a render, and read from a line."""

from __future__ import annotations

import dataclasses
import re

_MARKER = re.compile(r"<!-- rule: (?P<rule>[^\s@]+)(?: variant: (?P<variant>\S+))? -->")


@dataclasses.dataclass(frozen=True)
class Marker:
    """What a marker line says it is: a rule's default form, or one of its variants."""

    rule: str
    variant: str | None


def marker(rule: str, variant: str | None) -> str:
    """The marker line for a rule's default form (`variant` None) or for one of its variants."""

    if variant is None:
        return f"<!-- rule: {rule} -->"
    return f"<!-- rule: {rule} variant: {variant} -->"


def read_marker(line: str) -> Marker | None:
    """The marker a line is, or None where it is any other line."""

    found = _MARKER.fullmatch(line.rstrip())
    if found is None:
        return None
    return Marker(rule=found["rule"], variant=found["variant"])
