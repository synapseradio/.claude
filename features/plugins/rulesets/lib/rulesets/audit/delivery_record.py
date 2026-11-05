"""The shape of one delivery's record, written as a JSON object and read back as a typed value."""

from __future__ import annotations

import dataclasses
import hashlib
import json
import pathlib
from collections.abc import Mapping
from typing import Literal, get_args

from rulesets.audit import json_fields as fields
from rulesets.audit.json_fields import Document
from rulesets.compose.applying import SkippedBlock
from rulesets.compose.composition import DeliveredConflict
from rulesets.compose.precedence import Adds
from rulesets.compose.skipped import SkippedReference
from rulesets.delivery.parts import Body
from rulesets.facts.context import Absent, AllToolsBut, Facts, ListedTools
from rulesets.facts.model.fact import (
    Claimed,
    FromForceLever,
    FromVariable,
    Missing,
    ModelFact,
    Unclaimed,
)
from rulesets.notices import SHOWN, Notice, NoticeKind
from rulesets.session.state import Band, FlagSetting, SessionState

type Scope = Literal["session", "delegate", "switch"]
type RecordKind = Literal["session", "delegate", "fork"]

SCOPES: tuple[Scope, ...] = ("session", "delegate", "switch")
KINDS: tuple[RecordKind, ...] = ("session", "delegate", "fork")
NOTICE_KINDS: tuple[NoticeKind, ...] = get_args(NoticeKind.__value__)


@dataclasses.dataclass(frozen=True)
class RuleLine:
    """A rule delivered, with the SHA-256 digest of its body."""

    rule: str
    variant: str | None
    digest: str

    @classmethod
    def from_json(cls, source: Document) -> RuleLine:
        return cls(
            fields.text(source, "rule"),
            fields.text_or_none(source, "variant"),
            fields.text(source, "digest"),
        )


@dataclasses.dataclass(frozen=True)
class WithheldLine:
    rule: str
    error: str

    @classmethod
    def from_json(cls, source: Document) -> WithheldLine:
        return cls(fields.text(source, "rule"), fields.text(source, "error"))


@dataclasses.dataclass(frozen=True)
class SkippedReferenceLine:
    """A reference to an undeclared name, with the manifest file and line it stands on."""

    file: str
    line: int
    reference: str
    name: str

    @classmethod
    def of(cls, skipped: SkippedReference, file: pathlib.Path) -> SkippedReferenceLine:
        return cls(str(file), skipped.line, skipped.text, skipped.name)

    @classmethod
    def from_json(cls, source: Document) -> SkippedReferenceLine:
        return cls(
            fields.text(source, "file"),
            fields.whole_number(source, "line"),
            fields.text(source, "reference"),
            fields.text(source, "name"),
        )


@dataclasses.dataclass(frozen=True)
class SkippedBlockLine:
    """A block keyed on undeclared models or flags, with the manifest file and line it stands on."""

    file: str
    line: int
    condition: str
    names: tuple[str, ...]

    @classmethod
    def of(cls, skipped: SkippedBlock, file: pathlib.Path) -> SkippedBlockLine:
        names = (*skipped.undeclared.models, *skipped.undeclared.flags)
        return cls(str(file), skipped.line, skipped.condition, names)

    @classmethod
    def from_json(cls, source: Document) -> SkippedBlockLine:
        return cls(
            fields.text(source, "file"),
            fields.whole_number(source, "line"),
            fields.text(source, "condition"),
            fields.texts(source, "names"),
        )


@dataclasses.dataclass(frozen=True)
class StatementLine:
    """One statement of a conflict: the reference as written, its line, and the variant it set."""

    reference: str
    line: int
    variant: str

    @classmethod
    def from_json(cls, source: Document) -> StatementLine:
        return cls(
            fields.text(source, "reference"),
            fields.whole_number(source, "line"),
            fields.text(source, "variant"),
        )


@dataclasses.dataclass(frozen=True)
class ConflictLine:
    """Statements that set different variants of one rule, and the variant delivered (None: default)."""

    rule: str
    statements: tuple[StatementLine, ...]
    delivered: str | None

    @classmethod
    def of(cls, met: DeliveredConflict) -> ConflictLine:
        statements = tuple(
            StatementLine(s.source.text, s.source.line, s.says.variant)
            for s in met.conflict.statements
            if isinstance(s.says, Adds) and s.says.variant is not None
        )
        return cls(met.rule, statements, met.variant)

    @classmethod
    def from_json(cls, source: Document) -> ConflictLine:
        return cls(
            fields.text(source, "rule"),
            fields.each(source, "statements", StatementLine.from_json),
            fields.text_or_none(source, "delivered"),
        )


@dataclasses.dataclass(frozen=True)
class ReportedValue:
    """A non-string value a source reported as the model identifier, and its type."""

    value: object
    type: str


@dataclasses.dataclass(frozen=True)
class ModelLine:
    """The model fact: its declared name and identifier where claimed, with the source.

    `not_a_string` is set where the source named a value that is not a string.
    """

    state: Literal["claimed", "unclaimed", "missing"]
    name: str | None
    identifier: str | None
    source: str
    not_a_string: ReportedValue | None = None

    @classmethod
    def of(cls, fact: ModelFact) -> ModelLine:
        match fact:
            case Claimed(name, identifier, source):
                return cls("claimed", name, identifier, _label(source))
            case Unclaimed(identifier, source):
                return cls("unclaimed", None, identifier, _label(source))
            case Missing(not_a_string=None):
                return cls("missing", None, None, _label(fact.source))
            case Missing(not_a_string=reported):
                value = json.loads(json.dumps(reported.value, default=str))
                return cls(
                    "missing",
                    None,
                    None,
                    _label(fact.source),
                    ReportedValue(value, reported.type_name),
                )

    @classmethod
    def from_json(cls, source: Document) -> ModelLine:
        reported = source.get("not_a_string")
        return cls(
            fields.choice(source, "state", ("claimed", "unclaimed", "missing")),
            fields.text_or_none(source, "name"),
            fields.text_or_none(source, "identifier"),
            fields.text(source, "source"),
            None if reported is None else _reported_from_json(reported),
        )


def _reported_from_json(value: object) -> ReportedValue:
    reported = fields.document(value, "`not_a_string`")
    return ReportedValue(reported.get("value"), fields.text(reported, "type"))


@dataclasses.dataclass(frozen=True)
class AgentLine:
    """The agent fact where the context carries one."""

    name: str
    state: Literal["named"] = "named"


@dataclasses.dataclass(frozen=True)
class AbsentLine:
    """A fact the context lacks, with the reason it lacks it."""

    reason: str
    state: Literal["absent"] = "absent"


@dataclasses.dataclass(frozen=True)
class ToolsLine:
    """The tools fact and the definition file it came from.

    `tools` holds the tools a definition lists, or the tools it removes where `state` is `all-but`.
    """

    state: Literal["listed", "all-but"]
    tools: tuple[str, ...]
    source: str | None


def agent_line(agent: str | Absent, reason: str) -> AgentLine | AbsentLine:
    """The agent fact, or `reason` for its absence."""

    return AbsentLine(reason) if isinstance(agent, Absent) else AgentLine(agent)


def tools_line(facts: Facts, source: pathlib.Path | None, reason: str) -> ToolsLine | AbsentLine:
    """The tools fact with its definition file, or `reason` for its absence."""

    path = None if source is None else str(source)
    match facts.tools:
        case ListedTools(tools=tools):
            return ToolsLine("listed", tuple(sorted(tools)), path)
        case AllToolsBut(removed=removed):
            return ToolsLine("all-but", tuple(sorted(removed)), path)
        case _:
            return AbsentLine(reason)


def _agent_from_json(source: Document) -> AgentLine | AbsentLine:
    if fields.choice(source, "state", ("named", "absent")) == "absent":
        return AbsentLine(fields.text(source, "reason"))
    return AgentLine(fields.text(source, "name"))


def _tools_from_json(source: Document) -> ToolsLine | AbsentLine:
    if fields.choice(source, "state", ("listed", "all-but", "absent")) == "absent":
        return AbsentLine(fields.text(source, "reason"))
    return ToolsLine(
        fields.choice(source, "state", ("listed", "all-but")),
        fields.texts(source, "tools"),
        fields.text_or_none(source, "source"),
    )


@dataclasses.dataclass(frozen=True)
class FlagLine:
    """A flag the context held, with where it came from."""

    name: str
    source: Literal["launch", "toggle"]

    @classmethod
    def from_json(cls, source: Document) -> FlagLine:
        return cls(
            fields.text(source, "name"), fields.choice(source, "source", ("launch", "toggle"))
        )


@dataclasses.dataclass(frozen=True)
class StateFlagLine:
    """What a toggle did to a flag."""

    name: str
    setting: Literal["set", "unset"]

    @classmethod
    def from_json(cls, source: Document) -> StateFlagLine:
        return cls(fields.text(source, "name"), fields.choice(source, "setting", ("set", "unset")))


@dataclasses.dataclass(frozen=True)
class SessionStateLine:
    """The session state a delegate's delivery read, and the file it read it from."""

    path: str
    band: Literal["all", "none"] | None
    flags: tuple[StateFlagLine, ...]

    @classmethod
    def of(cls, path: pathlib.Path, state: SessionState) -> SessionStateLine:
        return cls(
            str(path),
            None if state.band is None else state.band.value,
            tuple(StateFlagLine(name, setting.value) for name, setting in state.flags.items()),
        )

    def state(self) -> SessionState:
        return SessionState(
            None if self.band is None else Band(self.band),
            {flag.name: FlagSetting(flag.setting) for flag in self.flags},
        )

    @classmethod
    def from_json(cls, source: Document) -> SessionStateLine:
        return cls(
            fields.text(source, "path"),
            fields.optional_choice(source, "band", ("all", "none")),
            fields.each(source, "flags", StateFlagLine.from_json),
        )


@dataclasses.dataclass(frozen=True)
class SwitchLine:
    """The model switch a delivery answered, with the prompt it ran under where the harness named one."""

    from_model: str | None
    to_model: str
    prompt_id: str | None

    @classmethod
    def from_json(cls, source: Document) -> SwitchLine:
        return cls(
            fields.text_or_none(source, "from_model"),
            fields.text(source, "to_model"),
            fields.text_or_none(source, "prompt_id"),
        )


def _notice_from_json(source: Document) -> Notice:
    return Notice(fields.choice(source, "kind", NOTICE_KINDS), fields.text(source, "subject"))


@dataclasses.dataclass(frozen=True)
class DeliveryRecord:
    """What one delivery composed and sent. `message_sent` says whether the person was shown a message.

    `part_count` is the number of parts the delivery carries, and `time_ns` orders the record
    among the later parts' records.
    """

    session_id: str
    agent_id: str | None
    scope: Scope
    kind: RecordKind
    time_ns: int
    agent: AgentLine | AbsentLine
    model: ModelLine
    tools: ToolsLine | AbsentLine
    flags: tuple[FlagLine, ...]
    session_state: SessionStateLine | None
    part_count: int
    rules: tuple[RuleLine, ...]
    withheld: tuple[WithheldLine, ...]
    skipped_references: tuple[SkippedReferenceLine, ...]
    skipped_blocks: tuple[SkippedBlockLine, ...]
    conflicts: tuple[ConflictLine, ...]
    left_out: tuple[str, ...]
    notices: tuple[Notice, ...]
    message_sent: bool
    switch: SwitchLine | None = None

    @property
    def writer(self) -> str:
        """`session` for the session's own records, the delegate identifier for a delegate's."""

        return self.agent_id or "session"

    def to_json(self) -> dict[str, object]:
        document = json.loads(json.dumps(dataclasses.asdict(self), default=str))
        document["notices"] = [
            {"kind": n.kind, "subject": n.subject, "shown": n.kind in SHOWN} for n in self.notices
        ]
        return document

    @classmethod
    def from_json(cls, source: Mapping[str, object]) -> DeliveryRecord:
        """The record a JSON object holds; `UnreadableRecord` where it is no delivery record."""

        state = source.get("session_state")
        switch = source.get("switch")
        return cls(
            session_id=fields.text(source, "session_id"),
            agent_id=fields.text_or_none(source, "agent_id"),
            scope=fields.choice(source, "scope", SCOPES),
            kind=fields.choice(source, "kind", KINDS),
            time_ns=fields.whole_number(source, "time_ns"),
            agent=_agent_from_json(fields.document(source.get("agent"), "`agent`")),
            model=ModelLine.from_json(fields.document(source.get("model"), "`model`")),
            tools=_tools_from_json(fields.document(source.get("tools"), "`tools`")),
            flags=fields.each(source, "flags", FlagLine.from_json),
            session_state=None
            if state is None
            else SessionStateLine.from_json(fields.document(state, "`session_state`")),
            part_count=fields.whole_number(source, "part_count"),
            rules=fields.each(source, "rules", RuleLine.from_json),
            withheld=fields.each(source, "withheld", WithheldLine.from_json),
            skipped_references=fields.each(
                source, "skipped_references", SkippedReferenceLine.from_json
            ),
            skipped_blocks=fields.each(source, "skipped_blocks", SkippedBlockLine.from_json),
            conflicts=fields.each(source, "conflicts", ConflictLine.from_json),
            left_out=fields.texts(source, "left_out"),
            notices=fields.each(source, "notices", _notice_from_json),
            message_sent=fields.truth(source, "message_sent"),
            switch=None
            if switch is None
            else SwitchLine.from_json(fields.document(switch, "`switch`")),
        )


def digest_of_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def digest_of(body: Body) -> str:
    return digest_of_text(body.text)


def _label(source: object) -> str:
    match source:
        case FromVariable(name=name, value=value):
            return f"{name}={value}"
        case FromForceLever(lever=lever):
            return lever.value
        case _:
            return str(source)
