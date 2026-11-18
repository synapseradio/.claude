#!/usr/bin/env -S uv run --frozen
"""The hook launcher runs delivery only on Python 3.15 or later with pyyaml.

A person's machine may hold several interpreters, and the newest one on the
path decides whether their sessions start with rules. Each case puts stub
interpreters on `PATH`, each answering the launcher's probe as one real
interpreter would, and runs `hooks/with-python.sh` as a hook command does.

Run with `uv run --frozen pytest features/plugins/rulesets/tests/test_launcher.py`.
"""

import json

import pytest
from launcher_stubs import launch, stub


@pytest.mark.parametrize(
    "interpreters",
    [
        [("python3", 14, True)],
        [("python3.15", 15, False), ("python3", 16, False)],
    ],
    ids=["only-python-3.14", "no-interpreter-with-the-yaml-library"],
)
def test_no_usable_interpreter_starts_the_session_without_rules_and_names_the_requirement(
    tmp_path, interpreters
) -> None:
    for name, minor, has_yaml in interpreters:
        stub(tmp_path, name, minor=minor, has_yaml=has_yaml)

    result = launch(tmp_path)

    assert result.returncode == 0, "a hook exiting non-zero reports an error in every session"
    assert result.stdout == "", "the session starts without the engine's rules"
    assert "3.15" in result.stderr, "stderr names the requirement the person must meet"


def test_python_3_15_with_the_yaml_library(tmp_path) -> None:
    stub(tmp_path, "python3.15", minor=15, has_yaml=True)
    stub(tmp_path, "python3", minor=14, has_yaml=True)

    result = launch(tmp_path)

    assert result.returncode == 0
    assert result.stdout == "ran by python3.15: deliver.py --part 1\n"


def test_python_3_15_without_the_yaml_library(tmp_path) -> None:
    stub(tmp_path, "python3.15", minor=15, has_yaml=False)
    stub(tmp_path, "python3", minor=16, has_yaml=True)

    result = launch(tmp_path)

    assert result.stdout == "ran by python3: deliver.py --part 1\n", (
        "the launcher skips an interpreter that cannot import yaml"
    )


def test_a_part_one_entry_sends_the_person_a_message_and_the_agent_nothing(tmp_path) -> None:
    stub(tmp_path, "python3", minor=14, has_yaml=True)

    result = launch(tmp_path, announce=True)

    output = json.loads(result.stdout)
    assert list(output) == ["systemMessage"], "only the person's message, never the agent's context"
    assert "3.15" in output["systemMessage"]


def test_an_entry_that_is_not_part_one_sends_nothing_to_stdout(tmp_path) -> None:
    stub(tmp_path, "python3", minor=14, has_yaml=True)

    assert launch(tmp_path).stdout == "", "ten entries would otherwise show the message ten times"
