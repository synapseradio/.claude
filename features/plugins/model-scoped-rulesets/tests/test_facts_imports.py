#!/usr/bin/env python3
"""Loading the delegate's model fact loads none of the resolver.

Serves the engineer who builds facts: `delegate` reaches the spawn records through
`audit`, and `audit` reads the resolver's state directory only where no directory is
passed. A module-level import there would pull the whole resolver, and the render and
corpus code it reads, into every caller that resolves a fact. Each case imports in a fresh
interpreter, since a module an earlier test imported stays in `sys.modules` for the rest
of the run.

Run with `python3.14 -m pytest features/plugins/model-scoped-rulesets/tests/test_facts_imports.py`.
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


class TestLoadingTheDelegatesModelFactLeavesTheResolverOut:
    def test_the_resolver_stays_unloaded(self):
        loaded = modules_loaded_by("rulesets.facts.model.delegate")

        assert "rulesets.facts.model.delegate" in loaded
        assert "rulesets.resolve" not in loaded

    def test_the_spawn_records_load_without_the_resolver_too(self):
        loaded = modules_loaded_by("rulesets.audit")

        assert "rulesets.audit" in loaded
        assert "rulesets.resolve" not in loaded
