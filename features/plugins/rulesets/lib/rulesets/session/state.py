"""The session state file: the toggle band a session has set."""

from __future__ import annotations

import dataclasses
import enum

import yaml

from rulesets.locations import Locations


class Band(enum.Enum):
    """The session band's list: the spread of every rule, or the removal of every rule."""

    ALL = "all"
    NONE = "none"


@dataclasses.dataclass(frozen=True)
class SessionState:
    band: Band | None = None


def _path(locations: Locations, session_id: str):
    return locations.state / "session" / f"{session_id}.yaml"


def read_state(locations: Locations, session_id: str) -> SessionState:
    """The state a session wrote; a missing file reads as the empty state."""

    path = _path(locations, session_id)
    if not path.is_file():
        return SessionState()
    document = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    band = document.get("band")
    return SessionState(Band(band) if band is not None else None)


def write_state(locations: Locations, session_id: str, state: SessionState) -> None:
    """Write the state by replacing the file in one step."""

    path = _path(locations, session_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    document = {} if state.band is None else {"band": state.band.value}
    temporary = path.with_suffix(".tmp")
    temporary.write_text(yaml.safe_dump(document), encoding="utf-8")
    temporary.replace(path)
