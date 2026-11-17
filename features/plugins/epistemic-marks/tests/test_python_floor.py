"""Every module the hooks run parses under Python 3.14.

    python3 -m unittest tests.test_python_floor -v

The launcher runs the hooks under a 3.14 interpreter that uv provisions, so a
module using syntax newer than 3.14 fails at the first hook run, and that
session starts with no rule and no check.
"""

import ast
import unittest
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
FLOOR = (3, 14)
SHIPPED = ("epistemic_marks", "hooks")


def shipped_sources() -> list[Path]:
    """Every Python file the plugin runs, tests excluded."""
    return sorted(path for directory in SHIPPED for path in (PLUGIN_ROOT / directory).rglob("*.py"))


class TheShippedCodeParsesAtTheFloor(unittest.TestCase):
    def test_it_checks_the_sources_the_hooks_run(self) -> None:
        checked = {path.relative_to(PLUGIN_ROOT).as_posix() for path in shipped_sources()}
        assert "epistemic_marks/scan.py" in checked, (
            "a floor test that misses the scanner proves nothing"
        )
        assert "hooks/verify-marks.py" in checked, "the entrypoint the harness runs"

    def test_every_module_parses_at_the_floor(self) -> None:
        for path in shipped_sources():
            with self.subTest(source=path.relative_to(PLUGIN_ROOT).as_posix()):
                try:
                    ast.parse(
                        path.read_text(encoding="utf-8"), filename=str(path), feature_version=FLOOR
                    )
                except SyntaxError as error:
                    self.fail(
                        f"{path.name}:{error.lineno} needs syntax newer than Python 3.14: "
                        f"{error.msg}"
                    )


class TheFormatterTargetsTheFloor(unittest.TestCase):
    def test_the_lint_target_is_the_floor(self) -> None:
        settings = PLUGIN_ROOT / ".ruff.toml"
        assert settings.is_file(), (
            "without a plugin .ruff.toml the formatter targets the repository's version"
        )
        assert 'target-version = "py314"' in settings.read_text(encoding="utf-8"), (
            "a formatter targeting a newer Python rewrites code to syntax the floor cannot parse"
        )


if __name__ == "__main__":
    unittest.main()
