"""Typed reads of one JSON object's fields, where a record is read back from the log."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from typing import cast

type Document = Mapping[str, object]


class UnreadableRecord(ValueError):
    """A line of the log that is no record of the shape asked for."""


def document(value: object, what: str) -> Document:
    if not isinstance(value, Mapping):
        raise UnreadableRecord(f"{what} is not an object")
    return value


def text(source: Document, key: str) -> str:
    value = source.get(key)
    if not isinstance(value, str):
        raise UnreadableRecord(f"`{key}` is not text")
    return value


def text_or_none(source: Document, key: str) -> str | None:
    return None if source.get(key) is None else text(source, key)


def whole_number(source: Document, key: str) -> int:
    value = source.get(key)
    if not isinstance(value, int) or isinstance(value, bool):
        raise UnreadableRecord(f"`{key}` is not a whole number")
    return value


def truth(source: Document, key: str) -> bool:
    value = source.get(key)
    if not isinstance(value, bool):
        raise UnreadableRecord(f"`{key}` is not true or false")
    return value


def choice[Allowed: str](source: Document, key: str, allowed: tuple[Allowed, ...]) -> Allowed:
    value = text(source, key)
    if value not in allowed:
        raise UnreadableRecord(f"`{key}` is none of {', '.join(allowed)}")
    return cast(Allowed, value)


def optional_choice[Allowed: str](
    source: Document, key: str, allowed: tuple[Allowed, ...]
) -> Allowed | None:
    return None if source.get(key) is None else choice(source, key, allowed)


def each[Parsed](
    source: Document, key: str, parse: Callable[[Document], Parsed]
) -> tuple[Parsed, ...]:
    """Each element of the list at `key`, parsed as an object."""

    return tuple(parse(document(item, f"an element of `{key}`")) for item in _list(source, key))


def texts(source: Document, key: str) -> tuple[str, ...]:
    items = _list(source, key)
    if not all(isinstance(item, str) for item in items):
        raise UnreadableRecord(f"`{key}` holds more than text")
    return tuple(cast(Sequence[str], items))


def _list(source: Document, key: str) -> list[object]:
    value = source.get(key)
    if not isinstance(value, list):
        raise UnreadableRecord(f"`{key}` is not a list")
    return value
