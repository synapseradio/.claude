"""A source file adopt leaves out, with the reason, as the report names it."""

from __future__ import annotations

import dataclasses

PATH_SCOPED = "path-scoped, so the harness loads it outside the engine"
NO_DEFAULT_FORM = "no default form holds this stem"


@dataclasses.dataclass(frozen=True)
class Skipped:
    """`name` is the file's path inside the source, in the form `<tier>/<stem>.md`."""

    name: str
    reason: str

    def line(self) -> str:
        return f"skipped {self.name}: {self.reason}"
