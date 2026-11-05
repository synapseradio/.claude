"""What reached each context of a session, one line per counted delivery."""

from __future__ import annotations

import dataclasses

from rulesets.audit import log
from rulesets.audit.counted import counted
from rulesets.audit.delivery_record import DeliveryRecord, Scope
from rulesets.locations import Locations

_NONE = "-"


@dataclasses.dataclass(frozen=True)
class ContextLine:
    """A delivery that reached a context: its scope, model, rules, flags, and delegate."""

    scope: Scope
    model: str
    model_source: str
    rule_count: int
    flags: tuple[str, ...]
    delegate: str | None

    def line(self) -> str:
        columns = [
            self.scope,
            self.model,
            self.model_source,
            str(self.rule_count),
            ",".join(self.flags) or _NONE,
        ]
        if self.delegate is not None:
            columns.append(self.delegate)
        return "\t".join(columns)


def deliveries(locations: Locations, session_id: str) -> tuple[ContextLine, ...]:
    """The session's counted deliveries in file order."""

    path = log.session_dir(locations, session_id) / log.DELIVERIES_FILE
    return tuple(
        _context_line(record) for record in counted(log.read_as(path, DeliveryRecord.from_json))
    )


def _context_line(record: DeliveryRecord) -> ContextLine:
    return ContextLine(
        scope=record.scope,
        model=record.model.name or record.model.identifier or _NONE,
        model_source=record.model.source,
        rule_count=len(record.rules),
        flags=tuple(flag.name for flag in record.flags),
        delegate=record.agent_id if record.scope == "delegate" else None,
    )
