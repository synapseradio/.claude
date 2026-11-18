"""Contract test for where the batch pass keeps its record of reported lines.

    python3 -m unittest discover -s tests -p test_ledger_location.py -v

README.md names three locations, in order: VERIFY_MARKS_STATE_DIR, then
`verify-marks` under CLAUDE_PLUGIN_DATA, then `epistemic-marks-verify-marks`
in the system temporary directory.
"""

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from epistemic_marks.ledger import state_dir


class TheStateDirectoryTakesTheFirstLocationNamed(unittest.TestCase):
    def test_the_record_goes_where_the_readme_says(self) -> None:
        rows = (
            (
                "the override wins over everything",
                {"VERIFY_MARKS_STATE_DIR": "/tmp/explicit", "CLAUDE_PLUGIN_DATA": "/tmp/data"},
                Path("/tmp/explicit"),
            ),
            (
                "plugin data comes next",
                {"CLAUDE_PLUGIN_DATA": "/tmp/data"},
                Path("/tmp/data") / "verify-marks",
            ),
            (
                "the system temporary directory is the last resort",
                {},
                Path(tempfile.gettempdir()) / "epistemic-marks-verify-marks",
            ),
        )
        for label, env, expected in rows:
            with self.subTest(label), patch.dict(os.environ, env, clear=True):
                assert state_dir() == expected


if __name__ == "__main__":
    unittest.main()
