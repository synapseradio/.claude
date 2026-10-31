"""Pins epistemic_marks.scan.last_turn_text's output while its cost changes.

    python3.14 -m pytest tests/test_scan_incremental.py -v

Written and confirmed green against the full-rescan implementation before
that implementation was touched, so a later change to how the function
reaches its answer is unable to also quietly change the answer: the
expected list below records real behavior observed against the old code,
not the new code's own idea of itself.

The fixture grows a transcript across nine stages, the way a real session's
file grows as PostToolBatch fires more than once inside one open turn and a
new turn then begins. It carries three turns, two tool round trips, and one
user message whose prose contains a JSON-boundary lookalike
(`{"type": "user"}`), so a fix that scans for that shape as text rather than
parsing each line as its own JSON object would misfire on it.

Every case sets VERIFY_MARKS_STATE_DIR to a private temporary directory, the
one ledger.py already resolves its own state through, since a fix that
persists a resume position writes there; the old implementation reads no
such variable and this fixture's assertions do not depend on it doing so.
"""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PLUGIN_ROOT))

from epistemic_marks.scan import last_turn_text  # noqa: E402


def entry(kind, content):
    return json.dumps({"type": kind, "message": {"role": kind, "content": content}})


def user_text(text):
    return entry("user", text)


def assistant_text(text):
    return entry("assistant", [{"type": "text", "text": text}])


def assistant_tool_use():
    return entry("assistant", [{"type": "tool_use", "id": "t1", "name": "Read", "input": {}}])


def tool_result():
    return entry("user", [{"type": "tool_result", "tool_use_id": "t1", "content": "ok"}])


BOUNDARY_LOOKALIKE_USER_MESSAGE = (
    "turn two, and by the way, a raw transcript line looks like "
    '{"type": "user"} in JSON, which this sentence now quotes'
)

# Each stage appends lines to the one before it, the way a real transcript
# only ever grows. Each entry pairs the appended lines with the exact turn
# `last_turn_text` must return once they land, observed against the
# full-rescan implementation before it changed.
STAGES = [
    ([user_text("turn one")], []),
    ([assistant_text("T1 answer A")], ["T1 answer A"]),
    ([assistant_tool_use(), tool_result()], ["T1 answer A"]),
    ([assistant_text("T1 answer B")], ["T1 answer A", "T1 answer B"]),
    ([user_text(BOUNDARY_LOOKALIKE_USER_MESSAGE)], []),
    ([assistant_text("T2 answer with a mark [?] here")], ["T2 answer with a mark [?] here"]),
    (
        [assistant_tool_use(), tool_result(), assistant_text("T2 answer continued")],
        ["T2 answer with a mark [?] here", "T2 answer continued"],
    ),
    ([user_text("turn three")], []),
    ([assistant_text("T3 first")], ["T3 first"]),
]


class LastTurnTextAcrossAGrowingTranscript(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.transcript = Path(self._tmp.name) / "session.jsonl"
        self.transcript.write_text("")
        self.state = Path(self._tmp.name) / "state"

    def append(self, lines):
        with open(self.transcript, "a") as f:
            for line in lines:
                f.write(line + "\n")

    def test_each_stage_of_growth_returns_the_turn_recorded_against_the_old_code(self):
        env = dict(os.environ)
        env["VERIFY_MARKS_STATE_DIR"] = str(self.state)
        with patch.dict(os.environ, env, clear=True):
            for stage_number, (new_lines, expected) in enumerate(STAGES, start=1):
                self.append(new_lines)
                with self.subTest(stage=stage_number):
                    self.assertEqual(last_turn_text(str(self.transcript)), expected)

    def test_repeated_calls_at_the_same_stage_stay_stable(self):
        # A batch pass that fires more than once before the transcript grows
        # again must see the same turn each time, not an empty one from
        # having already consumed its own boundary.
        env = dict(os.environ)
        env["VERIFY_MARKS_STATE_DIR"] = str(self.state)
        with patch.dict(os.environ, env, clear=True):
            for new_lines, _expected in STAGES:
                self.append(new_lines)
            self.assertEqual(last_turn_text(str(self.transcript)), ["T3 first"])
            self.assertEqual(last_turn_text(str(self.transcript)), ["T3 first"])
            self.assertEqual(last_turn_text(str(self.transcript)), ["T3 first"])


if __name__ == "__main__":
    unittest.main()
