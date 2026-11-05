"""What the delivery records say the main session's conversation holds."""

from __future__ import annotations

from rulesets.audit import log
from rulesets.audit.counted import counted
from rulesets.audit.delivery_record import DeliveryRecord
from rulesets.locations import Locations

type RuleKey = tuple[str, str | None]


def held_rules(locations: Locations, session_id: str) -> tuple[RuleKey, ...] | None:
    """The rules, each with its variant, of the main session's last counted delivery.

    None where no counted delivery of the main session is on record.
    """

    held = [
        record
        for record in counted(_records(locations, session_id))
        if record.scope in ("session", "switch")
    ]
    return tuple((rule.rule, rule.variant) for rule in held[-1].rules) if held else None


def supersedes_a_switch(locations: Locations, session_id: str, prompt_id: str | None) -> bool:
    """Whether a switch record already carries `prompt_id`, so a switch under it replaces that record."""

    return prompt_id is not None and any(
        _switched_under(record, prompt_id) for record in _records(locations, session_id)
    )


def _records(locations: Locations, session_id: str) -> list[DeliveryRecord]:
    path = log.session_dir(locations, session_id) / log.DELIVERIES_FILE
    return log.read_as(path, DeliveryRecord.from_json)


def _switched_under(record: DeliveryRecord, prompt_id: str) -> bool:
    return record.switch is not None and record.switch.prompt_id == prompt_id
