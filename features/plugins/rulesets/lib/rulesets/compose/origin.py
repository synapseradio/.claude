"""Which applying list a statement comes from: `defaults`, a block, or the session band."""

from __future__ import annotations

import dataclasses


@dataclasses.dataclass(frozen=True)
class DefaultsOrigin:
    """The `defaults` list."""


@dataclasses.dataclass(frozen=True)
class BlockOrigin:
    """A `when` block, by its condition as written."""

    condition: str


@dataclasses.dataclass(frozen=True)
class SessionBandOrigin:
    """The list a session's `all` or `none` toggle applies."""


type Origin = DefaultsOrigin | BlockOrigin | SessionBandOrigin
