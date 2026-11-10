"""Every module the hooks run parses under Python 3.9:

    python3 -m unittest tests.test_python_floor -v

The launcher accepts any interpreter from 3.9 up, so a module using syntax
newer than 3.9 fails at the first hook run on a machine whose newest Python is
3.9, and that session starts with no rule and no check.
"""

import ast
import unittest
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
FLOOR = (3, 9)
SHIPPED = ("epistemic_marks", "hooks")


def shipped_sources():
    """Every Python file the plugin runs, tests excluded."""

    return sorted(path for directory in SHIPPED for path in (PLUGIN_ROOT / directory).rglob("*.py"))


class TheShippedCodeParsesAtTheFloor(unittest.TestCase):
    def test_it_checks_the_sources_the_hooks_run(self):
        checked = {path.relative_to(PLUGIN_ROOT).as_posix() for path in shipped_sources()}
        self.assertIn(
            "epistemic_marks/scan.py",
            checked,
            "a floor test that misses the scanner proves nothing",
        )
        self.assertIn("hooks/verify-marks.py", checked, "the entrypoint the harness runs")

    def test_every_module_parses_at_the_floor(self):
        for path in shipped_sources():
            with self.subTest(source=path.relative_to(PLUGIN_ROOT).as_posix()):
                try:
                    ast.parse(
                        path.read_text(encoding="utf-8"), filename=str(path), feature_version=FLOOR
                    )
                except SyntaxError as error:
                    self.fail(
                        f"{path.name}:{error.lineno} needs syntax newer than Python 3.9: {error.msg}"
                    )


class TheFormatterTargetsTheFloor(unittest.TestCase):
    def test_the_lint_target_is_the_floor(self):
        # Read as text: tomllib arrived in Python 3.11, above the floor.
        settings = PLUGIN_ROOT / ".ruff.toml"
        self.assertTrue(
            settings.is_file(),
            "without a plugin .ruff.toml the formatter targets the repository's version",
        )
        self.assertIn(
            'target-version = "py39"',
            settings.read_text(encoding="utf-8"),
            "a formatter targeting a newer Python strips the parentheses a 3.9 parser needs",
        )


if __name__ == "__main__":
    unittest.main()
