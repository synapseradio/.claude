"""Which delivery records count as delivered."""

from __future__ import annotations

from collections.abc import Iterable

from rulesets.audit.delivery_record import DeliveryRecord


def counted(records: Iterable[DeliveryRecord]) -> tuple[DeliveryRecord, ...]:
    """The records that reached context, in file order.

    Switch records sharing one `prompt_id` mean no request ran between them, so only the last of
    them counts, a failed one included. A record of a failed delivery never counts, for it
    delivered nothing. A switch record with no `prompt_id` counts, and so does every other record.
    """

    kept = list(records)
    last_of: dict[str, int] = {}
    for position, record in enumerate(kept):
        if (prompt_id := _switch_prompt(record)) is not None:
            last_of[prompt_id] = position
    return tuple(
        record
        for position, record in enumerate(kept)
        if not _failed(record)
        and ((prompt_id := _switch_prompt(record)) is None or last_of[prompt_id] == position)
    )


def _switch_prompt(record: DeliveryRecord) -> str | None:
    return record.switch.prompt_id if record.switch else None


def _failed(record: DeliveryRecord) -> bool:
    return any(notice.kind == "delivery-failure" for notice in record.notices)
