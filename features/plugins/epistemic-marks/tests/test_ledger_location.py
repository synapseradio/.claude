"""Tests for where the batch pass keeps its record of reported lines.

    python3.14 -m pytest tests/test_ledger_location.py -v

The location matters for two reasons. Writing inside the plugin root loses
the record on every plugin update and fails outright where that root is read
only. Writing to a fixed path under somebody's home assumes a layout this
plugin has no business assuming.

Each case sets the environment through unittest.mock.patch.dict, the
framework's own primitive for it, and touches no filesystem.
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PLUGIN_ROOT))

from epistemic_marks.ledger import (  # noqa: E402
    PLUGIN_DATA_ENV,
    STATE_ENV,
    state_dir,
)

BOTH_UNSET = {STATE_ENV: "", PLUGIN_DATA_ENV: ""}


def with_env(**overrides):
    """The environment with both location variables cleared, then overridden."""
    cleared = dict(BOTH_UNSET)
    cleared.update(overrides)
    return {key: value for key, value in cleared.items() if value}


class TheStateDirectoryTakesTheFirstLocationNamed(unittest.TestCase):
    def test_the_explicit_override_wins_over_everything(self):
        env = with_env(**{STATE_ENV: "/tmp/explicit", PLUGIN_DATA_ENV: "/tmp/plugin-data"})
        with patch.dict(os.environ, env, clear=True):
            self.assertEqual(state_dir(), Path("/tmp/explicit"))

    def test_the_plugin_data_directory_comes_next(self):
        env = with_env(**{PLUGIN_DATA_ENV: "/tmp/plugin-data"})
        with patch.dict(os.environ, env, clear=True):
            self.assertEqual(state_dir().parent, Path("/tmp/plugin-data"))

    def test_absent_both_it_falls_back_to_the_system_temporary_directory(self):
        with patch.dict(os.environ, with_env(), clear=True):
            self.assertEqual(state_dir().parent, Path(tempfile.gettempdir()))


class TheStateDirectoryStaysOutOfPlacesItMustNotWrite(unittest.TestCase):
    """The two properties the location has to hold on any machine."""

    def cases(self):
        return (
            ("both unset", with_env()),
            ("plugin data named", with_env(**{PLUGIN_DATA_ENV: "/tmp/plugin-data"})),
        )

    def test_it_never_resolves_inside_the_plugin_root(self):
        for label, env in self.cases():
            with self.subTest(label), patch.dict(os.environ, env, clear=True):
                resolved = state_dir().resolve()
                self.assertFalse(
                    resolved.is_relative_to(PLUGIN_ROOT),
                    f"with {label} the record lands at {resolved}, inside the plugin "
                    "root, which a plugin update replaces and may mount read only",
                )

    def test_it_assumes_no_directory_layout_under_the_home_directory(self):
        for label, env in self.cases():
            with self.subTest(label), patch.dict(os.environ, env, clear=True):
                resolved = state_dir().resolve()
                self.assertFalse(
                    resolved.is_relative_to(Path.home()),
                    f"with {label} the record lands at {resolved}, under the home "
                    "directory, a layout this plugin must not assume",
                )


if __name__ == "__main__":
    unittest.main()
