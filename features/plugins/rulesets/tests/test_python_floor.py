#!/usr/bin/env -S uv run --frozen
"""Every module the hooks run parses under Python 3.15.

The launcher accepts any interpreter from 3.15 up, so a module using syntax
newer than 3.15 fails at the first hook run on a machine whose newest Python is
3.15, and that session starts with no rules.

Run with `uv run --frozen pytest features/plugins/rulesets/tests/test_python_floor.py`.
"""

import ast
import pathlib

import pytest

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]
FLOOR = (3, 15)


def sources() -> list[pathlib.Path]:
    """Every Python file the plugin runs, tests excluded."""
    return sorted([*(PLUGIN_ROOT / "lib").rglob("*.py"), *(PLUGIN_ROOT / "hooks").rglob("*.py")])


@pytest.mark.parametrize("path", sources(), ids=lambda path: str(path.relative_to(PLUGIN_ROOT)))
def test_the_module_parses_at_the_floor(path) -> None:
    try:
        ast.parse(path.read_text(encoding="utf-8"), filename=str(path), feature_version=FLOOR)
    except SyntaxError as error:
        pytest.fail(f"{path.name}:{error.lineno} needs syntax newer than Python 3.15: {error.msg}")
