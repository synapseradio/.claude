"""The model a caller named for one spawn, joined from the spawn records to a delegate's start."""

import pathlib
from dataclasses import dataclass

from rulesets import spawn_log
from rulesets.notices import Notice


@dataclass(frozen=True)
class SpawnModel:
    """What the spawn records say about one delegate: the model named, or why none is."""

    identifier: object = None
    notices: tuple[Notice, ...] = ()


def spawn_model(
    session_id: str | None,
    prompt_id: str | None,
    agent_type: str | None,
    state_dir: pathlib.Path,
) -> SpawnModel:
    """The model the caller named for the spawn that `prompt_id` and `agent_type` identify.

    A start missing one of the three fields cannot be joined and raises
    `per-spawn-unreadable`. Records that name different models for the pair raise
    `per-spawn-ambiguous` and name none.
    """

    missing = [
        field
        for field, value in (
            ("session_id", session_id),
            ("prompt_id", prompt_id),
            ("agent_type", agent_type),
        )
        if not value
    ]
    if missing or session_id is None:
        return SpawnModel(notices=(Notice("per-spawn-unreadable", ", ".join(missing)),))

    named: list[object] = []
    for model in spawn_log.read_spawns(session_id, prompt_id, agent_type, state_dir):
        if model not in named:
            named.append(model)
    if len(named) > 1:
        return SpawnModel(notices=(Notice("per-spawn-ambiguous", ", ".join(map(str, named))),))
    return SpawnModel(named[0] if named else None)
