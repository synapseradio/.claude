"""An empty rulesets directory created where none exists."""

from __future__ import annotations

import dataclasses
import pathlib

_EMPTY_MANIFEST = "models: []\nflags: []\ndefaults: []\n"


@dataclasses.dataclass(frozen=True)
class Scaffolded:
    """An empty pool and a manifest that declares nothing now stand at the root."""


@dataclasses.dataclass(frozen=True)
class AlreadyPresent:
    """A rulesets directory already stands at the root; nothing was written."""


@dataclasses.dataclass(frozen=True)
class ScaffoldFailed:
    reason: str


def scaffold(root: pathlib.Path) -> Scaffolded | AlreadyPresent | ScaffoldFailed:
    """Create the empty directory where `root` does not exist."""

    if root.exists():
        return AlreadyPresent()
    try:
        (root / "rules").mkdir(parents=True)
        (root / "manifest.yaml").write_text(_EMPTY_MANIFEST, encoding="utf-8")
    except OSError as failure:
        return ScaffoldFailed(failure.strerror or str(failure))
    return Scaffolded()
