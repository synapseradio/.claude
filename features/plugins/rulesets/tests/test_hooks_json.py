"""Every command `hooks/hooks.json` wires runs one of the plugin's hook scripts, through the launcher.

Serves every session the plugin delivers rules to: the harness runs each command as written, so a
command naming a missing script or an argument its script rejects delivers nothing. The rest of
the suite calls each script's entry function in-process; this file holds the commands to the
same scripts and arguments. It reads the file and starts no process.

The form each command takes is `bash "${CLAUDE_PLUGIN_ROOT}/hooks/with-python.sh" [--announce]
"${CLAUDE_PLUGIN_ROOT}/hooks/<script>" <arguments>`; `hooks/with-python.sh` names the session
start's part 1 as the one entry carrying `--announce`, so the person sees one message.

Run with `.venv/bin/python -m pytest features/plugins/rulesets/tests/test_hooks_json.py`.
"""

import json
import shlex

import pytest
from delivery_world import DELIVER, HOOKS, HOOKS_JSON, OPUS, HookResult, deliver, select_commands

PLUGIN_ROOT_VARIABLE = "${CLAUDE_PLUGIN_ROOT}"
LAUNCHER_WORD = f"{PLUGIN_ROOT_VARIABLE}/hooks/with-python.sh"
SCRIPT_PREFIX = f"{PLUGIN_ROOT_VARIABLE}/hooks/"
RECORD_SCRIPTS = {"record-load.py", "record-spawn.py"}
ALL_PARTS = [str(number) for number in range(1, 11)]

# A fork's conversation already holds its rules, so `deliver.py` answers it with nothing once
# its arguments parse, before it reads or writes any state.
FORKED = json.dumps(
    {"session_id": "s1", "source": "fork", "model": OPUS, "hook_event_name": "SessionStart"}
).encode("utf-8")


def hook_groups() -> dict[str, list[dict]]:
    return json.loads(HOOKS_JSON.read_text(encoding="utf-8"))["hooks"]


def wired_commands() -> list[tuple[str, str]]:
    """Each event with each command its groups hold, in file order."""
    return [
        (event, hook["command"])
        for event, groups in hook_groups().items()
        for group in groups
        for hook in group["hooks"]
    ]


def commands_for(event: str, value: str) -> list[str]:
    """The commands the harness runs for an event whose matcher field holds `value`."""
    return select_commands(hook_groups()[event], value)


def part_numbers(commands) -> list[str]:
    return [command.rsplit("--part ", 1)[1] for command in commands if "--part " in command]


def split_command(command: str) -> tuple[bool, str, list[str]]:
    """Whether the command announces, the script it names, and the script's arguments."""
    words = shlex.split(command)
    assert words[:2] == ["bash", LAUNCHER_WORD], f"runs through the launcher: {command}"
    announces = words[2] == "--announce"
    script_word, *arguments = words[3:] if announces else words[2:]
    assert script_word.startswith(SCRIPT_PREFIX), f"names a script in hooks/: {command}"
    return announces, script_word.removeprefix(SCRIPT_PREFIX), arguments


@pytest.fixture
def environ(tmp_path) -> dict[str, str]:
    return {
        "HOME": str(tmp_path / "home"),
        "XDG_CACHE_HOME": str(tmp_path / "cache"),
        "GIT_CONFIG_GLOBAL": str(tmp_path / "gitconfig"),
        "CLAUDE_CONFIG_DIR": str(tmp_path / "config"),
    }


def parses_under_deliver(arguments: list[str], environ: dict[str, str]) -> HookResult:
    result = deliver([str(DELIVER), *arguments], FORKED, environ)
    result.release()
    return result


COMMANDS = wired_commands()
COMMAND_IDS = [f"{event}-{index}" for index, (event, _) in enumerate(COMMANDS)]


class TestEveryCommandRunsAHookScriptThroughTheLauncher:
    def test_the_file_wires_commands_for_every_event_the_plugin_answers(self) -> None:
        assert sorted({event for event, _ in COMMANDS}) == [
            "InstructionsLoaded",
            "PostModelSwitch",
            "PreToolUse",
            "SessionEnd",
            "SessionStart",
            "SubagentStart",
        ]

    @pytest.mark.parametrize(("event", "command"), COMMANDS, ids=COMMAND_IDS)
    def test_the_command_names_a_script_the_plugin_ships(self, event, command) -> None:
        _, script, _ = split_command(command)

        assert (HOOKS / script).is_file(), f"{event} runs hooks/{script}, which is missing"

    @pytest.mark.parametrize(("event", "command"), COMMANDS, ids=COMMAND_IDS)
    def test_the_arguments_parse_under_the_scripts_own_parser(
        self, event, command, environ
    ) -> None:
        _, script, arguments = split_command(command)

        if script in RECORD_SCRIPTS:
            assert arguments == [], f"{event}: {script} takes no arguments, given {arguments}"
        else:
            assert script == "deliver.py", f"{event} runs an unknown script {script}"
            assert parses_under_deliver(arguments, environ) == HookResult(0, "", ""), (
                f"{event}: deliver.py rejects {arguments}"
            )

    def test_an_argument_deliver_rejects_fails_the_same_parse(self, environ) -> None:
        result = parses_under_deliver(["--part", "one"], environ)

        assert result.exit_code == 2, "an unparsable part number ends the run as a usage error"

    def test_only_the_session_starts_part_one_announces_a_missing_interpreter(self) -> None:
        announcing = [
            (event, split_command(command)[2])
            for event, command in COMMANDS
            if split_command(command)[0]
        ]

        assert announcing == [("SessionStart", ["--part", "1"])]


class TestEveryDeliveryEntryRunsWhateverStartsTheContext:
    @pytest.mark.parametrize("source", ["startup", "resume", "clear", "compact", "fork"])
    def test_every_session_start_entry_runs_for_each_source(self, source) -> None:
        assert part_numbers(commands_for("SessionStart", source)) == ALL_PARTS

    @pytest.mark.parametrize(
        "agent_type",
        ["general-purpose", "Explore", "Plan", "fork", "critic", "plugin:reviewer", ""],
    )
    def test_every_subagent_start_entry_runs_for_each_agent_type(self, agent_type) -> None:
        assert part_numbers(commands_for("SubagentStart", agent_type)) == ALL_PARTS

    @pytest.mark.parametrize("target", [OPUS, "claude-haiku-4-5", "glm-5", ""])
    def test_every_model_switch_entry_runs_for_each_target(self, target) -> None:
        assert part_numbers(commands_for("PostModelSwitch", target)) == ALL_PARTS

    @pytest.mark.parametrize("reason", ["clear", "resume", "logout", "prompt_input_exit", "other"])
    def test_the_session_end_entry_runs_for_each_reason(self, reason) -> None:
        assert [c for c in commands_for("SessionEnd", reason) if c.endswith("--end")]
