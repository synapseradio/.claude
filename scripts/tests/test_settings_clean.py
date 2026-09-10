#!/usr/bin/env python3
"""No hook this repository's settings file names belongs to a plugin.

Claude Code runs hooks from the settings files and from every installed
plugin, and it does not deduplicate across those sources. An entry left in
`settings.base.json` for a hook a plugin now ships delivers that hook twice:
one session receives its rules in duplicate, and the second copy is invisible
in the settings file a reader is looking at.

Run with `python3.14 -m pytest scripts/tests/test_settings_clean.py`.
"""

import json
import pathlib

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
SETTINGS = REPO_ROOT / "settings.base.json"
PLUGIN_ROOT = REPO_ROOT / "features" / "model-scoped-rulesets"
WIRING = PLUGIN_ROOT / "hooks" / "hooks.json"

# The script names the settings file used to run for this feature. A command
# naming either is an entry the plugin has taken over.
MOVED_SCRIPTS = ("rulesets-deliver.py", "rulesets-audit.py")


def commands(wiring: dict) -> list[tuple[str, str | None, str]]:
    """Each (event, matcher, command) a settings-shaped hooks mapping holds."""

    found = []
    for event, groups in wiring.items():
        for group in groups:
            for hook in group.get("hooks", []):
                found.append((event, group.get("matcher"), hook.get("command", "")))
    return found


def settings_hooks() -> list[tuple[str, str | None, str]]:
    return commands(json.loads(SETTINGS.read_text(encoding="utf-8")).get("hooks", {}))


def plugin_hooks() -> list[tuple[str, str | None, str]]:
    return commands(json.loads(WIRING.read_text(encoding="utf-8"))["hooks"])


class TestTheSettingsFileNamesNoPluginHook:
    def test_no_command_runs_a_script_the_plugin_ships(self):
        offenders = [
            (event, matcher, command)
            for event, matcher, command in settings_hooks()
            if any(name in command for name in MOVED_SCRIPTS)
        ]

        assert offenders == [], (
            "hooks do not deduplicate across sources, so an entry here beside the plugin's "
            "own delivers the same ruleset twice into one context"
        )

    def test_the_events_the_plugin_covers_carry_no_entry_of_the_feature_s_own(self):
        covered = {(event, matcher) for event, matcher, _ in plugin_hooks()}
        remaining = {
            (event, matcher)
            for event, matcher, command in settings_hooks()
            if (event, matcher) in covered and any(name in command for name in MOVED_SCRIPTS)
        }

        assert remaining == set(), (
            "each pair the plugin's wiring covers is a context the plugin already delivers "
            f"into: {sorted(remaining)}"
        )

    def test_a_hook_no_plugin_owns_is_left_alone(self):
        """The cut is scoped: a hook no plugin owns stays.

        `PostToolUse` and `PostToolUseFailure` both run
        search-after-repeated-failure.py, which belongs to no plugin. A cut
        that took the moved scripts' events instead of the moved scripts
        themselves would have taken these down too.
        """

        found = {
            (event, matcher)
            for event, matcher, command in settings_hooks()
            if "search-after-repeated-failure.py" in command
        }

        assert found == {("PostToolUse", None), ("PostToolUseFailure", None)}, (
            "search-after-repeated-failure.py belongs to no plugin, and a session missing it "
            "loses its failure-streak counting"
        )
