"""Tests for the rule text this plugin delivers into a session.

python3.14 -m pytest tests/test_delivery.py -v
"""

import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = PLUGIN_ROOT / "hooks" / "deliver-rule.py"
sys.path.insert(0, str(PLUGIN_ROOT))

from epistemic_marks.delivery import RULE_BODY, after_divider, rule_text  # noqa: E402
from epistemic_marks.marks import MARKS  # noqa: E402


def run_deliver(source="startup"):
    completed = subprocess.run(
        [sys.executable, str(SCRIPT)],
        input=json.dumps({"hook_event_name": "SessionStart", "source": source}),
        capture_output=True,
        text=True,
        check=False,
        env=dict(os.environ),
    )
    return completed.returncode, completed.stdout


class TheDeliveredTextIsTheTeachingHalf(unittest.TestCase):
    def test_the_divider_splits_the_note_from_the_rule(self):
        raw = "note for a reader\n---\nthe rule itself\n"
        self.assertEqual(after_divider(raw).strip(), "the rule itself")

    def test_text_without_a_divider_travels_whole(self):
        self.assertEqual(after_divider("just the rule").strip(), "just the rule")

    def test_the_shipped_text_drops_its_on_disk_note(self):
        self.assertNotIn(
            "A plugin update replaces this file",
            rule_text(),
            "the note addressed to a reader on disk must not reach the model",
        )

    def test_the_shipped_text_teaches_every_enforced_mark(self):
        delivered = rule_text()
        for token in MARKS:
            self.assertIn(
                token,
                delivered,
                f"the delivered text never teaches {token}, which the hooks block",
            )

    def test_an_unreadable_rule_file_yields_nothing(self):
        self.assertEqual(rule_text(RULE_BODY.parent / "absent.md"), "")


class TheHookDeliversOnEverySessionSource(unittest.TestCase):
    def context_of(self, out):
        specific = json.loads(out)["hookSpecificOutput"]
        self.assertEqual(specific["hookEventName"], "SessionStart")
        return specific["additionalContext"]

    def test_it_delivers_the_vocabulary(self):
        code, out = run_deliver()
        self.assertEqual(code, 0)
        context = self.context_of(out)
        for token in MARKS:
            self.assertIn(token, context)

    def test_it_delivers_again_after_a_compaction(self):
        code, out = run_deliver(source="compact")
        self.assertEqual(code, 0)
        self.assertIn(
            MARKS[0],
            self.context_of(out),
            "a compaction drops injected context, so this firing has to restore it",
        )

    def test_a_payload_it_cannot_parse_stops_it_quietly(self):
        completed = subprocess.run(
            [sys.executable, str(SCRIPT)],
            input="not json",
            capture_output=True,
            text=True,
            check=False,
            env=dict(os.environ),
        )
        self.assertEqual(completed.returncode, 0)
        self.assertEqual(completed.stdout.strip(), "")


if __name__ == "__main__":
    unittest.main()
