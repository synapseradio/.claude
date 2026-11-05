"""The model identifiers the engine's delivery records name."""

from __future__ import annotations

from rulesets import spawn_log
from rulesets.audit import log
from rulesets.audit.delivery_record import DeliveryRecord
from rulesets.locations import Locations


def recorded_identifiers(locations: Locations) -> tuple[str, ...]:
    """Each identifier a delivery record names, once, in session then file order."""

    root = spawn_log.audit_dir(locations.state)
    if not root.is_dir():
        return ()
    named: dict[str, None] = {}
    for session in sorted(root.iterdir()):
        for record in log.read_as(session / log.DELIVERIES_FILE, DeliveryRecord.from_json):
            if record.model.identifier:
                named[record.model.identifier] = None
    return tuple(named)
