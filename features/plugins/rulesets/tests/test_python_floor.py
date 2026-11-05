#!/usr/bin/env python3
"""Every module the hooks run parses under Python 3.14.

The launcher accepts any interpreter from 3.14 up, so a module using syntax
newer than 3.14 fails at the first hook run on a machine whose newest Python is
3.14, and that session starts with no rules.

Run with `python3.14 -m pytest features/plugins/rulesets/tests/test_python_floor.py`.
"""

import ast
import pathlib
import tomllib

import pytest

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]
FLOOR = (3, 14)


def sources() -> list[pathlib.Path]:
    """Every Python file the plugin runs, tests excluded."""

    return sorted([*(PLUGIN_ROOT / "lib").rglob("*.py"), *(PLUGIN_ROOT / "hooks").rglob("*.py")])


def test_the_plugin_holds_python_to_check():
    assert sources(), "a floor test that finds no source proves nothing"


@pytest.mark.parametrize("path", sources(), ids=lambda path: str(path.relative_to(PLUGIN_ROOT)))
def test_the_module_parses_at_the_floor(path):
    try:
        ast.parse(path.read_text(encoding="utf-8"), filename=str(path), feature_version=FLOOR)
    except SyntaxError as error:
        pytest.fail(f"{path.name}:{error.lineno} needs syntax newer than Python 3.14: {error.msg}")


def test_the_lint_target_is_the_floor():
    settings = tomllib.loads((PLUGIN_ROOT / ".ruff.toml").read_text(encoding="utf-8"))

    assert settings["target-version"] == f"py{FLOOR[0]}{FLOOR[1]}"
