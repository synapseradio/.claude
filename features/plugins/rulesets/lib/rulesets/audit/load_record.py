"""The shape of the record an instructions-loaded event leaves, written as JSON and read back."""

from __future__ import annotations

import dataclasses
from collections.abc import Mapping

from rulesets.audit import json_fields as fields

KIND = "load"


@dataclasses.dataclass(frozen=True)
class LoadRecord:
    """An instruction file the harness loaded into a session's context, and why."""

    session_id: str
    file_path: str
    load_reason: str

    def to_json(self) -> dict[str, object]:
        return {"kind": KIND, **dataclasses.asdict(self)}

    @classmethod
    def from_payload(cls, payload: object) -> LoadRecord:
        """The record an InstructionsLoaded payload holds; `UnreadableRecord` where it holds none."""

        source = fields.document(payload, "the payload")
        return cls(
            session_id=_nonempty(source, "session_id"),
            file_path=_nonempty(source, "file_path"),
            load_reason=_nonempty(source, "load_reason"),
        )

    @classmethod
    def from_json(cls, source: Mapping[str, object]) -> LoadRecord:
        """The record a JSON object holds; `UnreadableRecord` where it is no load record."""

        if fields.text(source, "kind") != KIND:
            raise fields.UnreadableRecord("the record is not a load record")
        return cls.from_payload(source)


def _nonempty(source: fields.Document, key: str) -> str:
    value = fields.text(source, key)
    if not value:
        raise fields.UnreadableRecord(f"`{key}` is empty")
    return value
