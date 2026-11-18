"""Contract test for the reported-lines record: it discloses no conversation text.

    python3 -m unittest discover -s tests -p test_ledger_content.py -v

README.md promises that the record holds a fingerprint of each line and never
its text. The record can land in a directory shared with other users.
"""

import tempfile
import unittest
from pathlib import Path

from support import assistant_text, isolated_environment, run_hook, user_text

SECRET = "The staging database holds 4.2 million patient rows [?]."
WORDS = ("staging", "database", "patient", "4.2 million")


class TheRecordHoldsNoTextOfAReportedLine(unittest.TestCase):
    def test_a_reported_line_leaves_no_word_of_itself_in_the_record(self) -> None:
        with tempfile.TemporaryDirectory() as scratch:
            root = Path(scratch)
            state = root / "state"
            transcript = root / "session.jsonl"
            transcript.write_text(
                "\n".join([user_text("how big is staging"), assistant_text(SECRET)]) + "\n"
            )
            payload = {
                "hook_event_name": "PostToolBatch",
                "session_id": "disclosure-case",
                "transcript_path": str(transcript),
                "tool_calls": [],
            }
            env = isolated_environment(root / "home", state_dir=state)
            code, out, err = run_hook(payload, "--batch", env=env)
            assert code == 0, err
            assert SECRET in out, "the report itself must still carry the line"
            files = sorted(state.glob("*"))
            assert files, "the batch pass must have written a record to check"
            for path in files:
                written = path.read_text()
                for fragment in (SECRET, *WORDS):
                    assert fragment not in written, (
                        f"{path.name} holds {fragment!r} from the reported line, "
                        "so the record discloses conversation text"
                    )


if __name__ == "__main__":
    unittest.main()
