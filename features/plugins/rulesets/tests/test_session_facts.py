#!/usr/bin/env python3
"""A session's model fact comes from the first source that names an identifier.

Serves the person who launches a session: the harness's reported model, then `ANTHROPIC_MODEL`,
then `ANTHROPIC_DEFAULT_MODEL`, then the model the session recorded in `models/<session>.json`
(`docs/records.md`). The first string stands, claimed or not. A switch takes its target. The
environment reaches each case as a mapping, so no test reads the real one.

Run with `python3.15 -m pytest features/plugins/rulesets/tests/test_session_facts.py`.
"""

import pathlib
import sys

import pytest
from delivery_world import HAIKU, OPUS

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN_ROOT / "lib"))

from rulesets import spawn_log  # noqa: E402  (path must be set before this import)
from rulesets.facts.model import fact as model_fact  # noqa: E402
from rulesets.facts.model import record as model_record  # noqa: E402
from rulesets.facts.model import session as session_model  # noqa: E402

MODELS = ["opus", "sonnet", "haiku", "fable"]
NOVA = "claude-nova-1"


@pytest.fixture
def state(tmp_path) -> pathlib.Path:
    return tmp_path / "state"


def standing(fact) -> tuple[str | None, str | None]:
    """The identifier a fact holds and the declared name that claims it, `None` where absent."""
    return getattr(fact, "identifier", None), model_fact.claimed_name(fact)


@pytest.mark.parametrize(
    ("payload", "env", "recorded", "expected"),
    [
        ({"model": OPUS}, {"ANTHROPIC_MODEL": HAIKU}, None, (OPUS, "opus")),
        ({}, {"ANTHROPIC_MODEL": HAIKU, "ANTHROPIC_DEFAULT_MODEL": OPUS}, None, (HAIKU, "haiku")),
        ({}, {"ANTHROPIC_DEFAULT_MODEL": OPUS}, None, (OPUS, "opus")),
        ({}, {"ANTHROPIC_MODEL": "", "ANTHROPIC_DEFAULT_MODEL": OPUS}, None, (OPUS, "opus")),
        ({"model": ""}, {"ANTHROPIC_MODEL": HAIKU}, None, (HAIKU, "haiku")),
        ({}, {"ANTHROPIC_MODEL": OPUS}, HAIKU, (OPUS, "opus")),
        ({}, {}, HAIKU, (HAIKU, "haiku")),
        ({}, {}, None, (None, None)),
        ({"model": NOVA}, {"ANTHROPIC_MODEL": OPUS}, None, (NOVA, None)),
        ({}, {"ANTHROPIC_MODEL": NOVA, "ANTHROPIC_DEFAULT_MODEL": OPUS}, OPUS, (NOVA, None)),
        ({}, {}, NOVA, (NOVA, None)),
        ({"model": OPUS}, {"CLAUDE_CONTEXT_COLLAPSE_MODEL": HAIKU}, None, (OPUS, "opus")),
        ({}, {"CLAUDE_CONTEXT_COLLAPSE_MODEL": HAIKU}, None, (None, None)),
    ],
    ids=[
        "the harness model decides over the environment",
        "ANTHROPIC_MODEL is read before ANTHROPIC_DEFAULT_MODEL",
        "ANTHROPIC_DEFAULT_MODEL names the model where ANTHROPIC_MODEL is unset",
        "an empty ANTHROPIC_MODEL counts as unset",
        "an empty harness model counts as none reported",
        "the environment is read ahead of the record",
        "only the record names a model",
        "nothing names a model",
        "an unclaimed harness identifier stands over the environment",
        "an unclaimed variable stands over the next variable and the record",
        "an unclaimed record stands",
        "a model variable meant for another mechanism changes nothing where the harness reports",
        "a model variable meant for another mechanism names no model",
    ],
)
def test_a_sessions_model_comes_from_the_first_source_that_names_one(
    state, payload, env, recorded, expected
) -> None:
    if recorded is not None:
        model_record.write_model_record("s1", recorded, state)

    resolution = session_model.resolve_session_model(
        {"session_id": "s1", **payload}, MODELS, env, state
    )

    assert standing(resolution.fact) == expected


def test_a_session_reads_no_record_but_its_own(state) -> None:
    model_record.write_model_record("other", HAIKU, state)

    resolution = session_model.resolve_session_model({"session_id": "s1"}, MODELS, {}, state)

    assert standing(resolution.fact) == (None, None)


@pytest.mark.parametrize(
    ("payload", "expected"),
    [
        ({"to_model": NOVA}, (NOVA, None)),
        ({"to_model": OPUS}, (OPUS, "opus")),
        ({"to_model": HAIKU, "model": OPUS, "from_model": OPUS}, (HAIKU, "haiku")),
        ({}, (None, None)),
    ],
    ids=[
        "an undeclared target is the identifier for the delivery that follows",
        "a declared target is claimed",
        "the target stands over the harness model",
        "a switch naming no target leaves the model missing",
    ],
)
def test_a_switch_takes_its_target(payload, expected) -> None:
    assert standing(session_model.resolve_switch_model(payload, MODELS).fact) == expected


class TestTheSessionsModelRecord:
    def test_a_written_identifier_reads_back_and_a_later_write_replaces_it(self, state) -> None:
        model_record.write_model_record("s1", OPUS, state)
        assert model_record.read_model_record("s1", state) == OPUS

        model_record.write_model_record("s1", HAIKU, state)

        assert model_record.read_model_record("s1", state) == HAIKU

    def test_a_session_id_cannot_leave_the_state_directory(self, state) -> None:
        path = model_record.model_record_path("../../escape", state)

        assert state in path.parents

    def test_the_record_lives_outside_the_directory_that_pruning_removes(self, state) -> None:
        record = model_record.model_record_path("s1", state)

        assert spawn_log.session_dir("s1", state) not in record.parents
