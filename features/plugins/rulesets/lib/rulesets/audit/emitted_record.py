"""The shape of the record each part after the first leaves of what it emitted."""

from __future__ import annotations

import dataclasses
import json
from collections.abc import Mapping

from rulesets.audit import json_fields as fields
from rulesets.audit.delivery_record import ModelLine

KIND = "emitted"


@dataclasses.dataclass(frozen=True)
class EmittedRecord:
    """Part `part` of `part_count`: the model fact, the rules it carried, and the digest of its text."""

    session_id: str
    agent_id: str | None
    time_ns: int
    part: int
    part_count: int
    model: ModelLine
    rules: tuple[str, ...]
    digest: str

    @property
    def writer(self) -> str:
        return self.agent_id or "session"

    def to_json(self) -> dict[str, object]:
        return {"kind": KIND, **json.loads(json.dumps(dataclasses.asdict(self)))}

    @classmethod
    def from_json(cls, source: Mapping[str, object]) -> EmittedRecord:
        """The record a JSON object holds; `UnreadableRecord` where it is no emitted record."""

        if fields.text(source, "kind") != KIND:
            raise fields.UnreadableRecord("the record is not an emitted record")
        return cls(
            session_id=fields.text(source, "session_id"),
            agent_id=fields.text_or_none(source, "agent_id"),
            time_ns=fields.whole_number(source, "time_ns"),
            part=fields.whole_number(source, "part"),
            part_count=fields.whole_number(source, "part_count"),
            model=ModelLine.from_json(fields.document(source.get("model"), "`model`")),
            rules=fields.texts(source, "rules"),
            digest=fields.text(source, "digest"),
        )
