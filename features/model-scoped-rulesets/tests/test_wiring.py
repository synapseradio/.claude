#!/usr/bin/env python3
"""The wiring names files that exist, in the one form the chooser understands.

Nothing in the corpus auto-loads, so `hooks/hooks.json` is the only channel
by which a session receives its user rules. A command naming a file that is
not there delivers nothing, and the harness reports no error the author would
see. That is the state these tests fail on.

Run with `python3.14 -m pytest features/model-scoped-rulesets/tests/test_wiring.py`.
"""

import json
import pathlib

import pytest

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]
HOOKS_JSON = PLUGIN_ROOT / "hooks" / "hooks.json"

PLACEHOLDER_ROOT = "${CLAUDE_PLUGIN_ROOT}"
CHOOSER = f'bash "{PLACEHOLDER_ROOT}/hooks/with-python.sh" '

# Every event and matcher the feature is wired to, as the settings file
# carried them before the plugin took them over.
EXPECTED_ENTRIES = {
    ("SessionStart", "startup"),
    ("SessionStart", "resume"),
    ("SessionStart", "clear"),
    ("SessionStart", "compact"),
    ("SessionStart", "fork"),
    ("SubagentStart", None),
    ("PostModelSwitch", None),
    ("InstructionsLoaded", None),
    ("PreToolUse", "Agent"),
}


def load(path: pathlib.Path = HOOKS_JSON) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def entries(wiring: dict) -> list[tuple[str, str | None, dict]]:
    """Each (event, matcher, hook) the wiring holds, one per command."""

    found = []
    for event, groups in wiring["hooks"].items():
        for group in groups:
            for hook in group["hooks"]:
                found.append((event, group.get("matcher"), hook))
    return found


def script_path(command: str, root: pathlib.Path) -> pathlib.Path:
    """The hook script one command runs, resolved against a plugin root.

    Raises ValueError where the command is not the chooser followed by one
    quoted script under the plugin root and nothing else, so a hand edit
    that drifts from the form fails here rather than in a session.
    """

    if not command.startswith(CHOOSER):
        raise ValueError(f"{command!r} does not run the interpreter chooser")
    rest = command[len(CHOOSER) :]
    if not rest.startswith(f'"{PLACEHOLDER_ROOT}/hooks/'):
        raise ValueError(f"{command!r} does not name a script under the plugin's hooks directory")
    quoted, _, tail = rest[1:].partition('"')
    if tail.strip():
        raise ValueError(f"{command!r} passes an argument beyond the script: {tail.strip()!r}")
    return root / quoted.replace(f"{PLACEHOLDER_ROOT}/", "")


class TestTheWiringCoversEveryEvent:
    def test_the_events_and_matchers_are_the_nine_the_feature_needs(self):
        found = {(event, matcher) for event, matcher, _ in entries(load())}

        assert found == EXPECTED_ENTRIES, (
            "an event the wiring drops is a context that receives no ruleset, and one it "
            "adds delivers a second copy of the same rules"
        )

    def test_every_command_carries_a_timeout(self):
        for event, _, hook in entries(load()):
            assert hook["type"] == "command", event
            assert hook["timeout"] == 5, (
                f"the {event} hook runs before a context is built, so it needs a bound "
                "past which the session starts without it"
            )


class TestTheWiringNamesFilesThatExist:
    def test_every_command_resolves_to_a_file_under_the_plugin_root(self):
        for event, _, hook in entries(load()):
            path = script_path(hook["command"], PLUGIN_ROOT)

            assert path.is_file(), (
                f"the {event} command names {path}, which is not there, so that event would "
                "deliver nothing and the harness would report no error"
            )

    def test_the_chooser_the_commands_name_is_there(self):
        assert (PLUGIN_ROOT / "hooks" / "with-python.sh").is_file()


class TestAWiringNamingAMissingFileFails:
    """The invalid state, written out: the wiring names a file nobody shipped."""

    def test_a_command_naming_a_missing_script_is_caught(self, tmp_path):
        wiring = load()
        wiring["hooks"]["SubagentStart"][0]["hooks"][0]["command"] = (
            f'{CHOOSER}"{PLACEHOLDER_ROOT}/hooks/gone.py"'
        )
        copy = tmp_path / "hooks.json"
        copy.write_text(json.dumps(wiring), encoding="utf-8")

        missing = [
            script_path(hook["command"], PLUGIN_ROOT)
            for _, _, hook in entries(load(copy))
            if not script_path(hook["command"], PLUGIN_ROOT).is_file()
        ]

        assert missing == [PLUGIN_ROOT / "hooks" / "gone.py"], (
            "the check has to name the one command that resolves to nothing, since that is "
            "the file a reader restores or a command a reader repoints"
        )

    def test_a_command_that_skips_the_chooser_is_caught(self):
        with pytest.raises(ValueError, match="chooser"):
            script_path(f'python3 "{PLACEHOLDER_ROOT}/hooks/deliver.py"', PLUGIN_ROOT)

    def test_a_command_naming_a_corpus_of_its_own_is_caught(self):
        """The wiring passes no flag, so the corpus is the installing user's.

        A command naming one would pin every install to a path from the
        author's machine, and the resolution order the code carries, flag
        then variable then configuration directory, would never be reached.
        """

        with pytest.raises(ValueError, match="beyond the script"):
            script_path(
                f'{CHOOSER}"{PLACEHOLDER_ROOT}/hooks/deliver.py" --root /somewhere/rulesets',
                PLUGIN_ROOT,
            )
