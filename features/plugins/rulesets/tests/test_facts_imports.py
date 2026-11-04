#!/usr/bin/env python3
"""Loading the delegate's model fact loads neither the command line nor check.

Serves the engineer who builds facts: `delegate` reaches the spawn records through
`spawn_log`, which takes its state directory as an argument. A module-level import of
the command line or check there would pull both, and the corpus code they read, into
every caller that resolves a fact. Each case imports in a fresh
interpreter, since a module an earlier test imported stays in `sys.modules` for the rest
of the run.

Run with `python3.14 -m pytest features/plugins/rulesets/tests/test_facts_imports.py`.
"""

import json
import pathlib
import subprocess
import sys

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]

REPORT_LOADED = "import json, sys; import {module}; print(json.dumps(sorted(sys.modules)))"


def modules_loaded_by(module: str) -> set[str]:
    """Every module a fresh interpreter holds after importing `module`."""

    result = subprocess.run(
        [sys.executable, "-c", REPORT_LOADED.format(module=module)],
        capture_output=True,
        check=True,
        cwd=PLUGIN_ROOT / "lib",
        text=True,
    )
    return set(json.loads(result.stdout))


HEAVY_MODULES = {"rulesets.cli", "rulesets.check"}


class TestLoadingTheDelegatesModelFactLeavesTheCommandsOut:
    def test_the_command_line_and_check_stay_unloaded(self):
        loaded = modules_loaded_by("rulesets.facts.model.delegate")

        assert "rulesets.facts.model.delegate" in loaded
        assert not loaded & HEAVY_MODULES

    def test_the_spawn_records_load_without_the_commands_too(self):
        loaded = modules_loaded_by("rulesets.spawn_log")

        assert "rulesets.spawn_log" in loaded
        assert not loaded & HEAVY_MODULES
