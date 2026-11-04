"""The flags a session launched with: those the manifest declares, and those it does not."""

from __future__ import annotations

import dataclasses
from collections.abc import Collection, Mapping

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
