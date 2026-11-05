"""The text a context receives for one rule, and the variant it came from."""

from __future__ import annotations

import dataclasses


@dataclasses.dataclass(frozen=True)
class DeliveredText:
    """A rule's bytes as delivered; `variant` is None for the default form."""

    text: bytes
    variant: str | None
