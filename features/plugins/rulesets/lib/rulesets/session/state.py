"""The session state file: the toggle band a session has set."""

from __future__ import annotations

import dataclasses
import enum
from collections.abc import Mapping

import yaml

from rulesets.locations import Locations


class Band(enum.Enum):
    """The session band's list: the spread of every rule, or the removal of every rule."""

    ALL = "all"
    NONE = "none"


class FlagSetting(enum.Enum):
    """What a toggle did to a flag: set it, or unset it over a launch flag."""

    SET = "set"
    UNSET = "unset"


@dataclasses.dataclass(frozen=True)
class SessionState:
    band: Band | None = None
    flags: Mapping[str, FlagSetting] = dataclasses.field(default_factory=dict)


def state_path(locations: Locations, session_id: str):
    """The file a session's state is kept in, whether or not it exists."""

    return locations.state / "session" / f"{session_id}.yaml"


def read_state(locations: Locations, session_id: str) -> SessionState:
    """The state a session wrote; a missing file reads as the empty state."""

    path = state_path(locations, session_id)
    if not path.is_file():
        return SessionState()
    document = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    band = document.get("band")
    flags = {name: FlagSetting(setting) for name, setting in (document.get("flags") or {}).items()}
    return SessionState(Band(band) if band is not None else None, flags)


def write_state(locations: Locations, session_id: str, state: SessionState) -> None:
    """Write the state by replacing the file in one step."""

    path = state_path(locations, session_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    document: dict[str, object] = {}
    if state.band is not None:
        document["band"] = state.band.value
    if state.flags:
        document["flags"] = {name: setting.value for name, setting in state.flags.items()}
    temporary = path.with_suffix(".tmp")
    temporary.write_text(yaml.safe_dump(document), encoding="utf-8")
    temporary.replace(path)


def remove_state(locations: Locations, session_id: str) -> None:
    """Remove the session's state file; a session with none stays as it is."""

    state_path(locations, session_id).unlink(missing_ok=True)


def copy_state(locations: Locations, from_id: str, to_id: str) -> None:
    """Give `to_id` the state `from_id` holds now; a source with none leaves `to_id` as it is."""

    if state_path(locations, from_id).is_file():
        write_state(locations, to_id, read_state(locations, from_id))
