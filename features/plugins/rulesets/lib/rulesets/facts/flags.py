"""The flags a context holds: those a session launched with, and the toggles a delegate adds."""

from __future__ import annotations

import dataclasses
import enum
from collections.abc import Collection, Mapping

from rulesets.session.state import FlagSetting, SessionState

LAUNCH_VARIABLE = "RULESETS_FLAGS"


@dataclasses.dataclass(frozen=True)
class LaunchFlags:
    """`declared` hold for the context; `undeclared` are dropped and drawn a notice."""

    declared: frozenset[str]
    undeclared: tuple[str, ...]


def launch_flags(environ: Mapping[str, str], declared: Collection[str]) -> LaunchFlags:
    """Read the comma-separated names in `RULESETS_FLAGS`, splitting them by the manifest's flags."""

    named = [name.strip() for name in environ.get(LAUNCH_VARIABLE, "").split(",")]
    named = list(dict.fromkeys(name for name in named if name))
    return LaunchFlags(
        frozenset(name for name in named if name in declared),
        tuple(name for name in named if name not in declared),
    )


class FlagSource(enum.Enum):
    """Where a held flag came from."""

    LAUNCH = "launch"
    TOGGLE = "toggle"


@dataclasses.dataclass(frozen=True)
class FlagFact:
    name: str
    source: FlagSource


def delegate_flags(launch: LaunchFlags, state: SessionState) -> tuple[FlagFact, ...]:
    """The launch flags, plus each flag a toggle set, minus each flag a toggle unset, by name."""

    held = {name: FlagSource.LAUNCH for name in launch.declared}
    for name, setting in state.flags.items():
        match setting:
            case FlagSetting.SET:
                held.setdefault(name, FlagSource.TOGGLE)
            case FlagSetting.UNSET:
                held.pop(name, None)
    return tuple(FlagFact(name, source) for name, source in sorted(held.items()))


def session_flags(launch: LaunchFlags) -> tuple[FlagFact, ...]:
    """The main session's flags: the launch flags alone, whatever a toggle set."""

    return tuple(FlagFact(name, FlagSource.LAUNCH) for name in sorted(launch.declared))
