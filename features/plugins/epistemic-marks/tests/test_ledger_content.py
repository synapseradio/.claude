"""Tests that the reported-lines record discloses no conversation text.

    python3 -m unittest discover -s tests -p test_ledger_content.py -v

The record can land in a directory shared with other users, so what it holds
is a disclosure question rather than a formatting one.
"""

import tempfile
import unittest
from pathlib import Path

from support import assistant_text, isolated_environment, run_hook, user_text

from epistemic_marks.ledger import fingerprint

SECRET = "The staging database holds 4.2 million patient rows [?]."
WORDS = ("staging", "database", "patient", "4.2 million", "holds")


class TheRecordHoldsIdentitiesAndNotText(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        root = Path(self._tmp.name)
        self.state = root / "state"
        self.env = isolated_environment(root / "home", state_dir=self.state)
        self.transcript = root / "session.jsonl"
        self.transcript.write_text(
            "\n".join([user_text("how big is staging"), assistant_text(SECRET)]) + "\n"
        )

    def run_batch(self) -> str:
        payload = {
            "hook_event_name": "PostToolBatch",
            "session_id": "disclosure-case",
            "transcript_path": str(self.transcript),
            "tool_calls": [],
        }
        code, out = run_hook(payload, "--batch", env=self.env)
        assert code == 0
        return out

    def written_files(self) -> list[Path]:
        return sorted(self.state.glob("*.json"))

    def test_the_flagged_line_reaches_the_model_through_the_context(self) -> None:
        assert SECRET in self.run_batch(), "the report itself must still carry the line"

    def test_no_written_record_contains_the_flagged_line(self) -> None:
        self.run_batch()
        files = self.written_files()
        assert files, "the batch pass must have written a record to check"
        for path in files:
            assert SECRET not in path.read_text(), (
                f"{path.name} holds the flagged line verbatim, so the record discloses "
                "the conversation text it deduplicated"
            )

    def test_no_written_record_contains_any_substring_of_the_flagged_line(self) -> None:
        self.run_batch()
        for path in self.written_files():
            written = path.read_text()
            for word in WORDS:
                assert word not in written, (
                    f"{path.name} holds {word!r} from the flagged line, so the record "
                    "leaks part of the conversation text"
                )

    def test_the_record_holds_the_fingerprint_that_identifies_the_line(self) -> None:
        self.run_batch()
        written = [path.read_text() for path in self.written_files()]
        assert any(fingerprint(SECRET) in text for text in written), (
            "the record must identify the line it reported, or the next batch "
            "reports the same line again"
        )

    def test_the_fingerprint_carries_none_of_the_line(self) -> None:
        digest = fingerprint(SECRET)
        for word in WORDS:
            assert word not in digest


if __name__ == "__main__":
    unittest.main()
