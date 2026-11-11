"""A toggle action applied to a session's state."""

from __future__ import annotations

import dataclasses
from collections.abc import Collection

from rulesets.session.state import Band, FlagSetting, SessionState


@dataclasses.dataclass(frozen=True)
class SetBand:
    band: Band


@dataclasses.dataclass(frozen=True)
class SetFlag:
    name: str


@dataclasses.dataclass(frozen=True)
class UnsetFlag:
    name: str


@dataclasses.dataclass(frozen=True)
class Clear:
    """End every toggle of the session."""


type ToggleAction = SetBand | SetFlag | UnsetFlag | Clear


@dataclasses.dataclass(frozen=True)
class UndeclaredFlag:
    name: str


def apply_toggle(
    declared_flags: Collection[str], state: SessionState, action: ToggleAction
) -> SessionState | UndeclaredFlag:
    """The state after `action`, or the flag name the config does not declare."""

    match action:
        case SetBand(band):
            return dataclasses.replace(state, band=band)
        case SetFlag(name) | UnsetFlag(name) if name not in declared_flags:
            return UndeclaredFlag(name)
        case SetFlag(name):
            return dataclasses.replace(state, flags={**state.flags, name: FlagSetting.SET})
        case UnsetFlag(name):
            return dataclasses.replace(state, flags={**state.flags, name: FlagSetting.UNSET})
        case Clear():
            return SessionState()
