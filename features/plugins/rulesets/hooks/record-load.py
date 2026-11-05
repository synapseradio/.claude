#!/usr/bin/env python3
"""Record each instruction file the harness loads; print nothing and exit 0."""

import json
import os
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "lib"))

from rulesets.audit import log
from rulesets.audit.json_fields import UnreadableRecord
from rulesets.audit.load_record import LoadRecord
from rulesets.locations import Locations


def main() -> int:
    try:
        record(json.loads(sys.stdin.read()), Locations.from_environment(os.environ))
    except Exception:
        return 0
    return 0


def record(payload: object, locations: Locations) -> None:
    """Append the load to its session's log; skip a payload that names no file, reason, or session."""

    try:
        loaded = LoadRecord.from_payload(payload)
    except UnreadableRecord:
        return
    log.append(log.session_dir(locations, loaded.session_id) / log.LOADS_FILE, loaded.to_json())


if __name__ == "__main__":
    sys.exit(main())
