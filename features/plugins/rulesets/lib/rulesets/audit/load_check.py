"""The check that no pool rule is auto-loaded by the harness, from a session's load records."""

from __future__ import annotations

import dataclasses
import pathlib

from rulesets.audit import log
from rulesets.audit.load_record import LoadRecord
from rulesets.locations import Locations
from rulesets.source.pool import read_pool

_CLAUDE_MD = "CLAUDE.md"


@dataclasses.dataclass(frozen=True)
class StillAutoLoading:
    """A loaded file whose stem is the name of `rule`, a rule of the pool."""

    rule: str
    path: str
    reason: str

    def line(self) -> str:
        return f"still auto-loading: {self.path} (reason {self.reason})"


def load_check(
    locations: Locations, session_id: str, root: pathlib.Path
) -> tuple[StillAutoLoading, ...]:
    """Each load record of the session naming a file whose stem is the name of a rule under `root`.

    A rule's name is the stem of its pool file up to any `@`. The manifest is never read.
    A file named `CLAUDE.md` is expected whatever the pool holds.
    """

    names = read_pool(root).rules.keys()
    path = log.session_dir(locations, session_id) / log.LOADS_FILE
    return tuple(
        StillAutoLoading(stem, record.file_path, record.load_reason)
        for record in log.read_as(path, LoadRecord.from_json)
        if pathlib.PurePath(record.file_path).name != _CLAUDE_MD
        and (stem := pathlib.PurePath(record.file_path).stem) in names
    )
