"""Which delivery records count as delivered."""

from __future__ import annotations

from collections.abc import Iterable, Mapping


def counted(records: Iterable[Mapping[str, object]]) -> tuple[Mapping[str, object], ...]:
    """The records that reached context, in file order.

    Switch records sharing one `prompt_id` mean no request ran between them, so only the last of
    them counts. A switch record with no `prompt_id` counts, and so does every other record.
    """

    kept = list(records)
    last_of: dict[object, int] = {}
    for position, record in enumerate(kept):
        prompt_id = _switch_prompt(record)
        if prompt_id is not None:
            last_of[prompt_id] = position
    return tuple(
        record
        for position, record in enumerate(kept)
        if (prompt_id := _switch_prompt(record)) is None or last_of[prompt_id] == position
    )


def _switch_prompt(record: Mapping[str, object]) -> object | None:
    switch = record.get("switch")
    return switch.get("prompt_id") if isinstance(switch, Mapping) else None
