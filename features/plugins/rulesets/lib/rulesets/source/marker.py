"""The rule marker comment: written before a rule's text in a render and in a delivery, and read from a line."""

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


def delivered(rule: str, text: str) -> str:
    """A rule's text as delivery puts it into a context: the rule's marker, a blank line, the text."""

    return f"{marker(rule, None)}\n\n{text}"
