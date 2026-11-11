"""Each counted delivery of a session recomposed from its record and compared with what was delivered."""

from __future__ import annotations

import dataclasses
import pathlib

from rulesets.audit import log
from rulesets.audit.counted import counted
from rulesets.audit.delivery_record import (
    AbsentLine,
    AgentLine,
    DeliveryRecord,
    ModelLine,
    ToolsLine,
    digest_of_text,
)
from rulesets.audit.emitted_record import EmittedRecord
from rulesets.compose.composition import Composition, compose
from rulesets.delivery.parts import MAX_PARTS, pack_parts
from rulesets.delivery.rule_bodies import bodies_of
from rulesets.facts.context import (
    ABSENT,
    UNCLAIMED,
    Absent,
    AllToolsBut,
    Facts,
    ListedTools,
    NoClaim,
)
from rulesets.locations import Locations
from rulesets.session.state import SessionState
from rulesets.source.directory import RulesetsDirectory, read_directory


@dataclasses.dataclass(frozen=True)
class Difference:
    """One way a delivery differs from its recomposition, named by the writer of the delivery."""

    writer: str
    text: str

    def line(self) -> str:
        return f"{self.writer}: {self.text}"


def delivery_check(
    locations: Locations, session_id: str, root: pathlib.Path
) -> tuple[Difference, ...]:
    """The differences between each counted delivery of the session and its recomposition now.

    The recomposition reads the config and pool under `root` as they stand, with the facts,
    flags, and session state the delivery's record names.
    """

    directory = read_directory(root)
    records = _deliveries(locations, session_id)
    emitted = _emitted(locations, session_id)
    found: list[Difference] = []
    for record in counted(records):
        composition = compose(directory, _facts_of(record), _state_of(record))
        found.extend(_rule_differences(record, composition))
        found.extend(_part_differences(record, composition, directory, records, emitted))
    return tuple(found)


def _deliveries(locations: Locations, session_id: str) -> tuple[DeliveryRecord, ...]:
    path = log.session_dir(locations, session_id) / log.DELIVERIES_FILE
    return tuple(log.read_as(path, DeliveryRecord.from_json))


def _emitted(locations: Locations, session_id: str) -> tuple[EmittedRecord, ...]:
    files = sorted(log.session_dir(locations, session_id).glob(log.EMITTED_PATTERN))
    return tuple(r for file in files for r in log.read_as(file, EmittedRecord.from_json))


def _facts_of(record: DeliveryRecord) -> Facts:
    match record.tools:
        case ToolsLine(state="listed", tools=tools):
            held = ListedTools(frozenset(tools))
        case ToolsLine(tools=tools):
            held = AllToolsBut(frozenset(tools))
        case AbsentLine():
            held = ABSENT
    return Facts(
        model=_model_fact(record.model),
        agent=record.agent.name if isinstance(record.agent, AgentLine) else ABSENT,
        kind=record.kind,
        flags=frozenset(flag.name for flag in record.flags),
        session=record.session_id,
        tools=held,
    )


def _model_fact(model: ModelLine) -> str | NoClaim | Absent:
    match model:
        case ModelLine(state="claimed", name=str() as name):
            return name
        case ModelLine(state="unclaimed"):
            return UNCLAIMED
        case _:
            return ABSENT


def _state_of(record: DeliveryRecord) -> SessionState:
    return record.session_state.state() if record.session_state else SessionState()


def _rule_differences(record: DeliveryRecord, composition: Composition) -> list[Difference]:
    delivered = {line.rule: line.variant for line in record.rules}
    composed = {rule.rule: rule.variant for rule in composition.rules}
    found: list[Difference] = []
    for rule in sorted(delivered.keys() | composed.keys()):
        if rule not in delivered:
            found.append(Difference(record.writer, f"{rule} composed but not delivered"))
        elif rule not in composed:
            found.append(Difference(record.writer, f"{rule} delivered but not composed"))
        elif delivered[rule] != composed[rule]:
            found.append(
                Difference(
                    record.writer,
                    f"{rule} delivered as {_name(delivered[rule])} but composed as "
                    f"{_name(composed[rule])}",
                )
            )
    return found


def _name(variant: str | None) -> str:
    return "default" if variant is None else variant


def _part_differences(
    record: DeliveryRecord,
    composition: Composition,
    directory: RulesetsDirectory,
    deliveries: tuple[DeliveryRecord, ...],
    emitted: tuple[EmittedRecord, ...],
) -> list[Difference]:
    """A line for each part after the first that was never emitted, or emitted differently."""

    composed = pack_parts(bodies_of(composition, directory.pool))[:MAX_PARTS]
    ends = [
        later.time_ns
        for later in deliveries
        if later.agent_id == record.agent_id and later.time_ns > record.time_ns
    ]
    until = min(ends, default=None)
    found: list[Difference] = []
    for number in range(2, record.part_count + 1):
        own = [
            entry
            for entry in emitted
            if entry.part == number
            and entry.session_id == record.session_id
            and entry.agent_id == record.agent_id
            and entry.time_ns > record.time_ns
            and (until is None or entry.time_ns < until)
        ]
        if not own:
            found.append(Difference(record.writer, f"part {number} composed and never emitted"))
            continue
        last = own[-1]
        if last.model != record.model:
            found.append(
                Difference(record.writer, f"part {number} emitted under a different model fact")
            )
        now = next((p for p in composed if p.index == number), None)
        text = now.text if now else None
        if text is None or digest_of_text(text) != last.digest:
            found.append(
                Difference(
                    record.writer, f"part {number} emitted text differs from what composes now"
                )
            )
    return found
