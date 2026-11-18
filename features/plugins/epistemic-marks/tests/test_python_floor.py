"""Every module the hooks run parses under Python 3.14.

    uv run --no-project --python 3.14 python -m unittest tests.test_python_floor -v

README.md names Python 3.14 as the floor. The launcher runs the hooks under a
3.14 interpreter that uv provisions, so a module using newer syntax fails at
the first hook run, and that session starts with no rule and no check.
"""

import ast
import unittest
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
FLOOR = (3, 14)
SHIPPED = ("epistemic_marks", "hooks")


class TheShippedCodeParsesAtTheFloor(unittest.TestCase):
    def test_every_module_parses_at_the_floor(self) -> None:
        sources = sorted(
            path for directory in SHIPPED for path in (PLUGIN_ROOT / directory).rglob("*.py")
        )
        assert sources, "no shipped source found to check"
        for path in sources:
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


if __name__ == "__main__":
    unittest.main()
