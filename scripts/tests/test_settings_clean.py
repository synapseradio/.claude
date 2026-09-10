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
import re

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
SETTINGS = REPO_ROOT / "settings.base.json"
PLUGIN_ROOT = REPO_ROOT / "features" / "model-scoped-rulesets"
WIRING = PLUGIN_ROOT / "hooks" / "hooks.json"

# The script names the settings file used to run for this feature. A command
# naming either is an entry the plugin has taken over.
MOVED_SCRIPTS = ("rulesets-deliver.py", "rulesets-audit.py")

# A quoted python filename, which is the form a forwarder names its target in.
SCRIPT_NAME = re.compile(r'"([a-z0-9-]+\.py)"')


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


class TestTheOldCommandPathsStillResolve:
    """The live settings file is untracked, so it can still name these.

    Nothing under the corpus auto-loads, so the only channel a session's user
    rules arrive by is a hook command. Until the live file names the plugin's
    own hooks, a command resolving to nothing leaves every session with none.

    `test_forwarders.py` holds the property every forwarder shares -- it is
    there, it resolves, and a missing target still exits zero and says so.
    What stays here is what only these two carry: a target named in the
    forwarder's own text, and the exact wording each one announces with.
    """

    def test_each_forwarder_names_a_target_the_plugin_ships(self):
        for name in MOVED_SCRIPTS:
            text = (REPO_ROOT / "scripts" / "hooks" / name).read_text(encoding="utf-8")
            targets = set(SCRIPT_NAME.findall(text)) - {name}

            assert targets, f"{name} names no script to forward to"
            for target in targets:
                assert (PLUGIN_ROOT / "hooks" / target).is_file(), (
                    f"{name} forwards to {target}, which the plugin does not ship, so the "
                    "old command path would resolve to nothing"
                )

    def test_the_delivery_forwarder_announces_a_missing_target_in_context(self, tmp_path):
        """A checkout where the plugin hook is gone is the window this file guards.

        The forwarder is copied into a tree with no `features/` beside it, so
        its target resolves to nothing, and it runs as the harness runs it.
        `CLAUDE_CONFIG_DIR` points into the temp tree so no live path is named.
        """

        import subprocess
        import sys

        hooks = tmp_path / "scripts" / "hooks"
        hooks.mkdir(parents=True)
        copy = hooks / "rulesets-deliver.py"
        copy.write_text(
            (REPO_ROOT / "scripts" / "hooks" / "rulesets-deliver.py").read_text(encoding="utf-8"),
            encoding="utf-8",
        )
        payload = {"hook_event_name": "SubagentStart", "session_id": "s1"}

        result = subprocess.run(
            [sys.executable, str(copy)],
            input=json.dumps(payload),
            capture_output=True,
            text=True,
            env={"PATH": "/usr/bin:/bin", "CLAUDE_CONFIG_DIR": str(tmp_path / "config")},
        )

        assert result.returncode == 0
        emitted = json.loads(result.stdout)["hookSpecificOutput"]
        assert emitted["hookEventName"] == "SubagentStart"
        assert "running without its user rules" in emitted["additionalContext"]
        assert (
            str(tmp_path / "features" / "model-scoped-rulesets" / "hooks" / "deliver.py")
            in (emitted["additionalContext"])
        )

    def test_the_audit_forwarder_announces_a_missing_target_in_the_audit_trail(self, tmp_path):
        """The audit forwarder guards the same window, with no context to write into.

        `InstructionsLoaded` carries no decision control, so nothing this
        hook emits reaches a session's context the way a delivery's stdout
        does. The gap it exists to cover is instead recorded where the hook
        already writes -- the audit trail under the state directory -- and
        the process still exits zero and prints nothing.
        """

        import subprocess
        import sys

        hooks = tmp_path / "scripts" / "hooks"
        hooks.mkdir(parents=True)
        copy = hooks / "rulesets-audit.py"
        copy.write_text(
            (REPO_ROOT / "scripts" / "hooks" / "rulesets-audit.py").read_text(encoding="utf-8"),
            encoding="utf-8",
        )
        payload = {
            "hook_event_name": "InstructionsLoaded",
            "session_id": "s1",
            "file_path": "/a.md",
            "load_reason": "session_start",
        }
        state = tmp_path / "config" / ".tmp" / "rulesets"

        result = subprocess.run(
            [sys.executable, str(copy)],
            input=json.dumps(payload),
            capture_output=True,
            text=True,
            env={"PATH": "/usr/bin:/bin", "CLAUDE_CONFIG_DIR": str(tmp_path / "config")},
        )

        assert result.returncode == 0
        assert result.stdout == ""
        assert result.stderr == ""
        record_file = state / "audit" / "s1" / "session.jsonl"
        assert record_file.is_file(), (
            "the gap the missing target leaves has to land somewhere a later read of the "
            "trail finds it, since nothing here reaches the session's context"
        )
        record = json.loads(record_file.read_text(encoding="utf-8").strip())
        assert record["kind"] == "gap"
        assert (
            str(tmp_path / "features" / "model-scoped-rulesets" / "hooks" / "record-load.py")
            in record["reason"]
        )
