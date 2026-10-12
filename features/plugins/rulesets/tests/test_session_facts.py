#!/usr/bin/env python3
"""A session's model fact comes from the first source that names an identifier.

Serves the person who launches a session and the engineer who builds its facts:
the harness's reported model, then `ANTHROPIC_MODEL`, then `ANTHROPIC_DEFAULT_MODEL`,
then the model the session recorded. The first string stands, claimed or not, and a
value that is not a string leaves the model missing. A switch takes its target. The
environment reaches each case as a mapping, so no test reads the real one.

Run with `python3.14 -m pytest features/rulesets/tests/test_session_facts.py`.
"""

import json
import pathlib
import sys

import pytest

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN_ROOT / "lib"))

from rulesets import audit  # noqa: E402  (path must be set before this import)
from rulesets.facts.model import fact as model_fact  # noqa: E402
from rulesets.facts.model import record as model_record  # noqa: E402
from rulesets.facts.model import session as session_model  # noqa: E402

MODELS = ["opus", "sonnet", "haiku", "fable"]
OPUS = "claude-opus-5-5"
HAIKU = "claude-haiku-4-5"
SEPARATE_MECHANISM_VARIABLES = (
    "CLAUDE_CODE_AUTO_MODE_MODEL",
    "CLAUDE_CODE_BG_CLASSIFIER_MODEL",
    "CLAUDE_CONTEXT_COLLAPSE_MODEL",
)


class ReadSpy(dict):
    """An environment that remembers each name the engine asked it for."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.reads: set[str] = set()

    def get(self, key, default=None):
        self.reads.add(key)
        return super().get(key, default)

    def __getitem__(self, key):
        self.reads.add(key)
        return super().__getitem__(key)

    def __contains__(self, key):
        self.reads.add(key)
        return super().__contains__(key)


@pytest.fixture
def state(tmp_path):
    return tmp_path / "state"


def session_fact(payload, env=None, *, state_dir, models=MODELS):
    return session_model.resolve_session_model(payload, models, env or {}, state_dir).fact


class TestASessionsModelFactComesFromHarnessThenEnvironmentThenRecord:
    def test_the_harness_model_decides_and_the_environment_is_not_read(self, state):
        env = ReadSpy({"ANTHROPIC_MODEL": HAIKU, "ANTHROPIC_DEFAULT_MODEL": HAIKU})

        fact = session_fact({"model": OPUS, "session_id": "s1"}, env, state_dir=state)

        assert fact == model_fact.Claimed("opus", OPUS, "harness-reported")
        assert not env.reads & {"ANTHROPIC_MODEL", "ANTHROPIC_DEFAULT_MODEL"}

    def test_anthropic_model_is_read_before_anthropic_default_model(self, state):
        env = {"ANTHROPIC_MODEL": HAIKU, "ANTHROPIC_DEFAULT_MODEL": OPUS}

        fact = session_fact({"session_id": "s1"}, env, state_dir=state)

        assert fact == model_fact.Claimed(
            "haiku", HAIKU, model_fact.FromVariable("ANTHROPIC_MODEL", HAIKU)
        )

    def test_anthropic_default_model_is_read_only_where_anthropic_model_is_unset(self, state):
        env = ReadSpy({"ANTHROPIC_MODEL": HAIKU, "ANTHROPIC_DEFAULT_MODEL": OPUS})

        session_fact({"session_id": "s1"}, env, state_dir=state)

        assert "ANTHROPIC_DEFAULT_MODEL" not in env.reads

    def test_anthropic_default_model_names_the_model_where_anthropic_model_is_unset(self, state):
        env = {"ANTHROPIC_DEFAULT_MODEL": OPUS}

        fact = session_fact({"session_id": "s1"}, env, state_dir=state)

        assert fact == model_fact.Claimed(
            "opus", OPUS, model_fact.FromVariable("ANTHROPIC_DEFAULT_MODEL", OPUS)
        )

    def test_an_empty_anthropic_model_counts_as_unset(self, state):
        env = {"ANTHROPIC_MODEL": "", "ANTHROPIC_DEFAULT_MODEL": OPUS}

        fact = session_fact({"session_id": "s1"}, env, state_dir=state)

        assert fact.source == model_fact.FromVariable("ANTHROPIC_DEFAULT_MODEL", OPUS)

    def test_an_empty_harness_model_counts_as_none_reported(self, state):
        env = {"ANTHROPIC_MODEL": HAIKU}

        fact = session_fact({"model": "", "session_id": "s1"}, env, state_dir=state)

        assert model_fact.claimed_name(fact) == "haiku"

    def test_an_alias_in_a_variable_resolves_through_its_profile_variable(self, state):
        env = {"ANTHROPIC_MODEL": "haiku", "ANTHROPIC_DEFAULT_HAIKU_MODEL": HAIKU}

        fact = session_fact({"session_id": "s1"}, env, state_dir=state)

        assert fact == model_fact.Claimed(
            "haiku", HAIKU, model_fact.FromVariable("ANTHROPIC_MODEL", "haiku")
        )

    def test_only_the_record_names_a_model(self, state):
        model_record.write_model_record("s1", HAIKU, state)

        fact = session_fact({"session_id": "s1"}, {}, state_dir=state)

        assert fact == model_fact.Claimed("haiku", HAIKU, "session-record")

    def test_the_environment_is_read_ahead_of_the_record(self, state):
        model_record.write_model_record("s1", HAIKU, state)

        fact = session_fact({"session_id": "s1"}, {"ANTHROPIC_MODEL": OPUS}, state_dir=state)

        assert model_fact.claimed_name(fact) == "opus"

    def test_the_record_of_another_session_is_not_read(self, state):
        model_record.write_model_record("other", HAIKU, state)

        assert session_fact({"session_id": "s1"}, {}, state_dir=state) == model_fact.Missing()

    def test_nothing_names_a_model(self, state):
        fact = session_fact({"session_id": "s1"}, {}, state_dir=state)

        assert fact == model_fact.Missing()
        assert fact.source == "no-identifier"

    def test_a_payload_with_no_session_id_reads_no_record(self, state):
        model_record.write_model_record("s1", HAIKU, state)

        assert session_fact({}, {}, state_dir=state) == model_fact.Missing()


class TestASessionsFirstIdentifierStands:
    def test_an_unclaimed_harness_identifier_stands_and_the_environment_is_not_read(self, state):
        env = ReadSpy({"ANTHROPIC_MODEL": OPUS})

        fact = session_fact({"model": "claude-nova-1", "session_id": "s1"}, env, state_dir=state)

        assert fact == model_fact.Unclaimed("claude-nova-1", "harness-reported")
        assert not env.reads & {"ANTHROPIC_MODEL", "ANTHROPIC_DEFAULT_MODEL"}

    def test_a_non_string_harness_identifier_leaves_the_model_missing(self, state):
        env = ReadSpy({"ANTHROPIC_MODEL": OPUS})

        fact = session_fact({"model": 12345, "session_id": "s1"}, env, state_dir=state)

        assert fact == model_fact.Missing(model_fact.NotAString(12345, "harness-reported"))
        assert not env.reads & {"ANTHROPIC_MODEL", "ANTHROPIC_DEFAULT_MODEL"}

    def test_a_mapping_in_the_payload_leaves_the_model_missing_with_its_type(self, state):
        fact = session_fact({"model": {"id": OPUS}}, {"ANTHROPIC_MODEL": OPUS}, state_dir=state)

        assert fact == model_fact.Missing(model_fact.NotAString({"id": OPUS}, "harness-reported"))
        assert fact.not_a_string.type_name == "dict"

    def test_a_zero_is_a_number_and_not_an_absent_identifier(self, state):
        fact = session_fact({"model": 0}, {"ANTHROPIC_MODEL": OPUS}, state_dir=state)

        assert fact == model_fact.Missing(model_fact.NotAString(0, "harness-reported"))

    def test_an_unclaimed_variable_stands_over_the_next_variable_and_the_record(self, state):
        model_record.write_model_record("s1", OPUS, state)
        env = {"ANTHROPIC_MODEL": "claude-nova-1", "ANTHROPIC_DEFAULT_MODEL": OPUS}

        fact = session_fact({"session_id": "s1"}, env, state_dir=state)

        assert fact == model_fact.Unclaimed(
            "claude-nova-1", model_fact.FromVariable("ANTHROPIC_MODEL", "claude-nova-1")
        )

    def test_an_unclaimed_record_stands(self, state):
        model_record.write_model_record("s1", "claude-nova-1", state)

        fact = session_fact({"session_id": "s1"}, {}, state_dir=state)

        assert fact == model_fact.Unclaimed("claude-nova-1", "session-record")


class TestASwitchTakesItsTarget:
    def test_the_target_is_the_identifier_for_the_delivery_that_follows(self):
        payload = {"hook_event_name": "PostModelSwitch", "to_model": "claude-nova-1"}

        fact = session_model.resolve_switch_model(payload, MODELS, {}).fact

        assert fact == model_fact.Unclaimed("claude-nova-1", "switch-target")

    def test_a_declared_target_is_claimed(self):
        fact = session_model.resolve_switch_model({"to_model": OPUS}, MODELS, {}).fact

        assert fact == model_fact.Claimed("opus", OPUS, "switch-target")

    def test_the_target_stands_over_the_harness_model_and_the_environment(self):
        payload = {"to_model": HAIKU, "model": OPUS, "from_model": OPUS}
        env = ReadSpy({"ANTHROPIC_MODEL": OPUS})

        fact = session_model.resolve_switch_model(payload, MODELS, env).fact

        assert model_fact.claimed_name(fact) == "haiku"
        assert not env.reads & {"ANTHROPIC_MODEL", "ANTHROPIC_DEFAULT_MODEL"}

    def test_a_non_string_target_leaves_the_model_missing(self):
        fact = session_model.resolve_switch_model(
            {"to_model": 7}, MODELS, {"ANTHROPIC_MODEL": OPUS}
        ).fact

        assert fact == model_fact.Missing(model_fact.NotAString(7, "switch-target"))

    def test_a_switch_naming_no_target_leaves_the_model_missing(self):
        assert session_model.resolve_switch_model({}, MODELS, {}).fact == model_fact.Missing()


class TestAnUnclaimedOrMissingIdentifierMakesEveryModelTestFalse:
    def test_a_claude_model_before_its_name_is_declared(self, state):
        fact = session_fact({"model": "claude-nova-1"}, models=MODELS, state_dir=state)

        assert isinstance(fact, model_fact.Unclaimed)
        assert model_fact.claimed_name(fact) is None

    def test_a_claude_model_once_its_name_is_declared(self, state):
        fact = session_fact({"model": "claude-nova-1"}, models=[*MODELS, "nova"], state_dir=state)

        assert model_fact.claimed_name(fact) == "nova"

    def test_no_source_names_a_model(self, state):
        fact = session_fact({"session_id": "s1"}, {}, state_dir=state)

        assert isinstance(fact, model_fact.Missing)
        assert model_fact.claimed_name(fact) is None

    def test_a_non_string_identifier_leaves_the_model_missing_and_names_value_and_type(self, state):
        fact = session_fact({"model": 3.5}, {}, state_dir=state)

        assert model_fact.claimed_name(fact) is None
        assert (fact.not_a_string.value, fact.not_a_string.type_name) == (3.5, "float")


class TestTheEngineReadsNoVariableThatNamesASeparateMechanismsModel:
    def test_a_collapse_model_changes_nothing(self, state):
        payload = {"model": OPUS, "session_id": "s1"}
        collapse = {"CLAUDE_CONTEXT_COLLAPSE_MODEL": HAIKU}

        assert session_fact(payload, collapse, state_dir=state) == session_fact(
            payload, {}, state_dir=state
        )

    @pytest.mark.parametrize("payload", [{"model": OPUS}, {"session_id": "s1"}, {"model": 5}])
    def test_no_session_resolution_asks_for_any_of_the_three(self, state, payload):
        env = ReadSpy({name: HAIKU for name in SEPARATE_MECHANISM_VARIABLES})

        session_fact(payload, env, state_dir=state)
        session_model.resolve_switch_model({"to_model": OPUS}, MODELS, env)

        assert not env.reads & set(SEPARATE_MECHANISM_VARIABLES)


class TestTheSessionsModelRecord:
    def test_a_written_identifier_reads_back(self, state):
        assert model_record.write_model_record("s1", OPUS, state) is True

        assert model_record.read_model_record("s1", state) == OPUS

    def test_a_later_write_replaces_the_earlier_one(self, state):
        model_record.write_model_record("s1", OPUS, state)
        model_record.write_model_record("s1", HAIKU, state)

        assert model_record.read_model_record("s1", state) == HAIKU

    def test_a_session_with_no_record_reads_none(self, state):
        assert model_record.read_model_record("s1", state) is None

    def test_a_session_that_fell_open_records_the_absence_and_reads_none(self, state):
        model_record.write_model_record("s1", None, state)

        path = model_record.model_record_path("s1", state)
        assert "no model identifier was available" in path.read_text(encoding="utf-8")
        assert model_record.read_model_record("s1", state) is None

    def test_a_record_that_does_not_parse_reads_none(self, state):
        path = model_record.model_record_path("s1", state)
        path.parent.mkdir(parents=True)
        path.write_text("{not json", encoding="utf-8")

        assert model_record.read_model_record("s1", state) is None

    def test_a_record_holding_a_non_string_reads_none(self, state):
        path = model_record.model_record_path("s1", state)
        path.parent.mkdir(parents=True)
        path.write_text(json.dumps({"identifier": 12}), encoding="utf-8")

        assert model_record.read_model_record("s1", state) is None

    def test_a_write_leaves_no_temporary_file_beside_the_record(self, state):
        model_record.write_model_record("s1", OPUS, state)

        assert [p.name for p in model_record.model_record_path("s1", state).parent.iterdir()] == [
            model_record.model_record_path("s1", state).name
        ]

    def test_a_session_id_cannot_leave_the_state_directory(self, state):
        path = model_record.model_record_path("../../escape", state)

        assert state in path.parents

    def test_the_record_lives_apart_from_the_log(self, state):
        record = model_record.model_record_path("s1", state)

        assert audit.session_dir("s1", state) not in record.parents
        assert record.parent != audit.session_dir("s1", state)

    def test_an_unwritable_state_directory_answers_false_and_raises_nothing(self, tmp_path):
        blocker = tmp_path / "blocker"
        blocker.write_text("a file where the directory belongs", encoding="utf-8")

        assert model_record.write_model_record("s1", OPUS, blocker) is False
