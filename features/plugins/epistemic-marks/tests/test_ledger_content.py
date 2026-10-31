"""Tests that the reported-lines record discloses no conversation text.

    python3.14 -m pytest tests/test_ledger_content.py -v

The record can land in a directory shared with other users, so what it holds
is a disclosure question rather than a formatting one.
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = PLUGIN_ROOT / "hooks" / "verify-marks.py"
sys.path.insert(0, str(PLUGIN_ROOT))

from epistemic_marks.ledger import fingerprint  # noqa: E402

SECRET = "The staging database holds 4.2 million patient rows [?]."
WORDS = ("staging", "database", "patient", "4.2 million", "holds")


def entry(kind, content):
    return json.dumps({"type": kind, "message": {"role": kind, "content": content}})


class TheRecordHoldsIdentitiesAndNotText(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.state = Path(self._tmp.name) / "state"
        self.transcript = Path(self._tmp.name) / "session.jsonl"
        self.transcript.write_text(
            "\n".join(
                [
                    entry("user", "how big is staging"),
                    entry("assistant", [{"type": "text", "text": SECRET}]),
                ]
            )
            + "\n"
        )

    def run_batch(self):
        payload = {
            "hook_event_name": "PostToolBatch",
            "session_id": "disclosure-case",
            "transcript_path": str(self.transcript),
            "tool_calls": [],
        }
        inherited = {
            key: value
            for key, value in os.environ.items()
            if key not in ("VERIFY_MARKS_STATE_DIR", "CLAUDE_PLUGIN_DATA")
        }
        completed = subprocess.run(
            [sys.executable, str(SCRIPT), "--batch"],
            input=json.dumps(payload),
            capture_output=True,
            text=True,
            check=False,
            env={**inherited, "VERIFY_MARKS_STATE_DIR": str(self.state)},
        )
        self.assertEqual(completed.returncode, 0)
        return completed.stdout

    def written_files(self):
        return sorted(self.state.glob("*.json"))

    def test_the_flagged_line_reaches_the_model_through_the_context(self):
        self.assertIn(SECRET, self.run_batch(), "the report itself must still carry the line")

    def test_no_written_record_contains_the_flagged_line(self):
        self.run_batch()
        files = self.written_files()
        self.assertTrue(files, "the batch pass must have written a record to check")
        for path in files:
            written = path.read_text()
            self.assertNotIn(
                SECRET,
                written,
                f"{path.name} holds the flagged line verbatim, so the record discloses "
                "the conversation text it deduplicated",
            )

    def test_no_written_record_contains_any_substring_of_the_flagged_line(self):
        self.run_batch()
        for path in self.written_files():
            written = path.read_text()
            for word in WORDS:
                self.assertNotIn(
                    word,
                    written,
                    f"{path.name} holds {word!r} from the flagged line, so the record "
                    "leaks part of the conversation text",
                )

    def test_the_record_holds_the_fingerprint_that_identifies_the_line(self):
        self.run_batch()
        written = [path.read_text() for path in self.written_files()]
        self.assertTrue(
            any(fingerprint(SECRET) in text for text in written),
            "the record must identify the line it reported, or the next batch "
            "reports the same line again",
        )

    def test_the_fingerprint_carries_none_of_the_line(self):
        digest = fingerprint(SECRET)
        for word in WORDS:
            self.assertNotIn(word, digest)


if __name__ == "__main__":
    unittest.main()
