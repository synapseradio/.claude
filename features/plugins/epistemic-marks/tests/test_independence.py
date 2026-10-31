"""Tests binding this plugin's independence from everything outside it:

    python3.14 -m pytest tests/test_independence.py -v

`epistemic-marks` installs and works on a machine that has never seen a
ruleset corpus, a marketplace cache, or a `~/.claude` of any shape. That is
the reason the plugin ships its own rule text at all: were the corpus allowed
to carry the stem, delivery would be someone else's job and this plugin would
enforce a vocabulary it does not own.

README.md states the promise in prose. These are the checks that hold it.
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PLUGIN_ROOT))

from epistemic_marks.delivery import after_divider  # noqa: E402

# The rule's one home, named here rather than imported, so a delivery pointed
# somewhere else fails the comparison instead of moving it.
SHIPPED_RULE_BODY = PLUGIN_ROOT / "rule-text" / "epistemic-marks.md"

# Every way a source file could reach outside the plugin root: a home
# directory, a sibling plugin, a marketplace cache, or a walk upward through
# a literal parent segment. rule-text/ is out of scope, since its note above
# the divider is prose for a maintainer and stays correct by hand.
SCANNED = ("epistemic_marks", "hooks")
REACHES_OUTSIDE = ("~/.claude", "rulesets", "plugins/cache", "../", '".."', "'..'")


def scanned_sources():
    for directory in SCANNED:
        for path in sorted((PLUGIN_ROOT / directory).iterdir()):
            if path.suffix in (".py", ".sh"):
                yield path


class NoSourceReachesOutsideThePluginRoot(unittest.TestCase):
    def test_no_source_file_names_a_path_it_does_not_own(self):
        for path in scanned_sources():
            text = path.read_text()
            for reach in REACHES_OUTSIDE:
                with self.subTest(source=path.name, reach=reach):
                    # assertFalse over the membership, not assertNotIn over the
                    # file, so a hit names the reach rather than dumping the source.
                    self.assertFalse(
                        reach in text,
                        f"{path.name} names {reach!r}, so this plugin now depends on a "
                        "layout it does not own and cannot verify",
                    )

    def test_it_scans_the_sources_that_could_reach(self):
        scanned = {path.name for path in scanned_sources()}
        self.assertIn("delivery.py", scanned, "the one module that opens a file")
        self.assertIn("verify-marks.py", scanned, "the entrypoint the harness runs")


class DeliveryNeedsNothingOutsideThePlugin(unittest.TestCase):
    """A home directory with nothing in it changes nothing about the rule."""

    def rule_text_under(self, home):
        source = "from epistemic_marks.delivery import rule_text; print(rule_text())"
        completed = subprocess.run(
            [sys.executable, "-c", source],
            capture_output=True,
            text=True,
            check=False,
            cwd=str(PLUGIN_ROOT),
            env={**os.environ, "HOME": home, "PYTHONPATH": str(PLUGIN_ROOT)},
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        return completed.stdout.strip()

    def test_the_rule_body_arrives_whole_with_an_empty_home(self):
        with tempfile.TemporaryDirectory() as empty:
            delivered = self.rule_text_under(empty)
        self.assertEqual(
            delivered,
            after_divider(SHIPPED_RULE_BODY.read_text()).strip(),
            "the rule arrived short of its shipped body on a machine whose home "
            "directory holds nothing, so delivery reads a file it does not ship",
        )


class TheHooksNameNoSiblingPlugin(unittest.TestCase):
    def test_the_wiring_runs_nothing_outside_the_plugin_root(self):
        wiring = json.loads((PLUGIN_ROOT / "hooks" / "hooks.json").read_text())["hooks"]
        for event, matchers in wiring.items():
            for matcher in matchers:
                for hook in matcher["hooks"]:
                    with self.subTest(event=event):
                        self.assertEqual(
                            hook["command"].count("${CLAUDE_PLUGIN_ROOT}"),
                            2,
                            "every path a hook command names is the harness's own "
                            "handle on this plugin's root, launcher and script both",
                        )


if __name__ == "__main__":
    unittest.main()
