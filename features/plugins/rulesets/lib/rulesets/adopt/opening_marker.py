"""A source file's opening rule marker, which delivery writes and a pool file therefore omits."""

from __future__ import annotations

from rulesets.source.marker import delivered, marker


def _opening_line(rule: str) -> bytes:
    return f"{marker(rule, None)}\n".encode()


def without_own_marker(rule: str, data: bytes) -> bytes:
    """`data` less its opening line where that is exactly the marker for `rule`, and the blank line after it."""

    line = _opening_line(rule)
    if not data.startswith(line):
        return data
    return data[len(line) :].removeprefix(b"\n")


def under_delivery_marker(rule: str, data: bytes) -> bytes:
    """`data` as delivery would deliver a rules-folder file: under its marker unless it opens with one."""

    if data.startswith(_opening_line(rule)):
        return data
    return delivered(rule, "").encode() + data
