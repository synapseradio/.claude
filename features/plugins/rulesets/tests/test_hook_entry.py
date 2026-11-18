#!/usr/bin/env python3
"""Each hook's entry function, called in-process, answers as its script answers.

Serves every session the plugin delivers rules to: a hook script is one call of its entry
function, so the exit code, stdout, and stderr asserted here are what the harness reads. Each
expected value is the script's own output for the same configuration directory and payload.

Run with `.venv/bin/python -m pytest features/plugins/rulesets/tests/test_hook_entry.py`.
"""

import json
import pathlib

import pytest
from delivery_world import HOOKS, OPUS, core_rules_config, scratch_environment
from rulesets.hook_entry import HookResult, deliver, record_load, record_spawn

RULE = "Hold every rule as mandatory: café, naïve, 日本語.\n"
CONTEXT = json.dumps(f"<!-- rule: core-rules -->\n\n{RULE}")[1:-1]
SESSION_START = {
    "session_id": "s1",
    "source": "startup",
    "model": OPUS,
    "hook_event_name": "SessionStart",
}


@pytest.fixture
def config(tmp_path) -> pathlib.Path:
    """A configuration directory whose pool gives every context one rule."""
    return core_rules_config(tmp_path, RULE)


@pytest.fixture
def environ(tmp_path, config) -> dict[str, str]:
    return scratch_environment(tmp_path)


def payload(fields: dict) -> bytes:
    return json.dumps(fields).encode("utf-8")


def deliver_argv(*arguments: str) -> list[str]:
    return [str(HOOKS / "deliver.py"), *arguments]


def state(config: pathlib.Path) -> pathlib.Path:
    return config / ".tmp" / "rulesets-engine"


class TestDeliverAnswersEachEventAsTheScriptDoes:
    def test_a_session_start_first_part_prints_the_rules_as_session_context(self, environ) -> None:
        result = deliver(deliver_argv("--part", "1"), payload(SESSION_START), environ)

        assert result == HookResult(
            exit_code=0,
            stdout='{"hookSpecificOutput": {"hookEventName": "SessionStart", '
            f'"additionalContext": "{CONTEXT}"}}}}',
            stderr="",
        )

    def test_a_subagent_start_first_part_prints_the_rules_as_delegate_context(
        self, environ
    ) -> None:
        start = {
            "session_id": "s1",
            "agent_id": "a1",
            "agent_type": "critic",
            "prompt_id": "p1",
            "hook_event_name": "SubagentStart",
        }

        result = deliver(deliver_argv("--part", "1"), payload(start), environ)

        assert result == HookResult(
            exit_code=0,
            stdout='{"hookSpecificOutput": {"hookEventName": "SubagentStart", '
            f'"additionalContext": "{CONTEXT}"}}}}',
            stderr="",
        )

    def test_a_model_switch_with_no_earlier_delivery_prints_nothing(self, environ) -> None:
        switch = {
            "session_id": "s1",
            "from_model": "claude-haiku-4-5",
            "to_model": OPUS,
            "requested_model": "opus",
            "source": "command",
            "prompt_id": "p1",
            "hook_event_name": "PostModelSwitch",
        }

        result = deliver(deliver_argv("--part", "1"), payload(switch), environ)

        assert result == HookResult(exit_code=0, stdout="", stderr="")

    def test_a_session_end_prints_nothing(self, environ) -> None:
        end = {"session_id": "s1", "hook_event_name": "SessionEnd", "reason": "other"}

        result = deliver(deliver_argv("--end"), payload(end), environ)

        assert result == HookResult(exit_code=0, stdout="", stderr="")


class TestDeliverNeverFailsTheSessionStart:
    def test_a_payload_that_is_not_utf_8_delivers_nothing_and_exits_zero(self, environ) -> None:
        result = deliver(deliver_argv("--part", "1"), b"\xff\xfe{", environ)

        assert (result.exit_code, result.stdout) == (0, "")
        assert result.stderr, "the reason reaches stderr"

    def test_a_state_directory_it_cannot_write_exits_zero_and_tells_the_person_in_a_system_message(
        self, environ, config
    ) -> None:
        (config / ".tmp").write_text("", encoding="utf-8")

        result = deliver(deliver_argv("--part", "1"), payload(SESSION_START), environ)

        assert result.exit_code == 0, "a hook exiting non-zero reports an error in every session"
        assert list(json.loads(result.stdout)) == ["systemMessage"]

    def test_arguments_naming_no_part_exit_2_with_nothing_on_stdout(self, environ) -> None:
        result = deliver(deliver_argv(), b"{}", environ)

        assert (result.exit_code, result.stdout) == (2, "")


class TestTheRecordHooksWriteTheirLogUnderTheMappingsConfiguration:
    def test_an_instructions_load_is_appended_to_the_sessions_loads_and_prints_nothing(
        self, environ, config
    ) -> None:
        load = {
            "session_id": "s1",
            "transcript_path": "/work/s1.jsonl",
            "cwd": "/work",
            "hook_event_name": "InstructionsLoaded",
            "file_path": "/work/CLAUDE.md",
            "memory_type": "Project",
            "load_reason": "session_start",
        }

        result = record_load([str(HOOKS / "record-load.py")], payload(load), environ)

        assert result == HookResult(exit_code=0, stdout="", stderr="")
        assert (state(config) / "audit" / "s1" / "loads.jsonl").read_text(encoding="utf-8") == (
            '{"kind": "load", "session_id": "s1", "file_path": "/work/CLAUDE.md", '
            '"load_reason": "session_start"}\n'
        )

    def test_an_agent_spawn_is_appended_to_the_sessions_spawns_and_prints_nothing(
        self, environ, config
    ) -> None:
        spawn = {
            "session_id": "s1",
            "prompt_id": "p1",
            "transcript_path": "/work/s1.jsonl",
            "cwd": "/work",
            "permission_mode": "default",
            "hook_event_name": "PreToolUse",
            "tool_name": "Agent",
            "tool_use_id": "toolu_01ABC123",
            "tool_input": {
                "prompt": "Review",
                "description": "Review",
                "subagent_type": "critic",
                "model": "haiku",
            },
        }

        result = record_spawn([str(HOOKS / "record-spawn.py")], payload(spawn), environ)

        assert result == HookResult(exit_code=0, stdout="", stderr="")
        assert (state(config) / "audit" / "s1" / "spawns.jsonl").read_text(encoding="utf-8") == (
            '{"kind": "spawn", "session_id": "s1", "prompt_id": "p1", "agent_type": "critic", '
            '"model": "haiku"}\n'
        )
