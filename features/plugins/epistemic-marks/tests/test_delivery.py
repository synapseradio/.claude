"""Contract tests for what the plugin delivers into a session, run from the plugin root.

    uv run --no-project --python 3.14 python -m unittest discover -s tests -p test_delivery.py -v

README.md promises rule text at every session start and subagent start, from
a plugin that reads none of the user's configuration, teaching the four marks
the hooks enforce.
"""

import json
import re
import tempfile
import unittest
from pathlib import Path

from support import PLUGIN_ROOT, isolated_environment, run_hook

from epistemic_marks.marks import MARKS

DELIVER = PLUGIN_ROOT / "hooks" / "deliver-rule.py"
SHIPPED_RULE_BODY = PLUGIN_ROOT / "rule-text" / "epistemic-marks.md"

# The README's marks table.
README_MARKS = {"[?]", "[.?]", "[^?]", "[!?]"}

# Wider than the four marks, so a mark the rule teaches and nothing enforces
# shows up as an extra.
MARK_SHAPED = re.compile(r"\[[^\]\w\s]{0,3}\?\]")


class TheHookDeliversTheMarksOnEveryStart(unittest.TestCase):
    def test_each_start_delivers_the_four_marks_into_the_models_context_only(self) -> None:
        starts = (
            ("a session start", {"hook_event_name": "SessionStart", "source": "startup"}),
            (
                "a start after a compaction",
                {"hook_event_name": "SessionStart", "source": "compact"},
            ),
            ("a subagent start", {"hook_event_name": "SubagentStart"}),
        )
        for label, payload in starts:
            with self.subTest(start=label), tempfile.TemporaryDirectory() as scratch:
                # An empty home and no plugin data: the rule text ships with the plugin.
                env = isolated_environment(Path(scratch) / "home")
                code, out, err = run_hook(payload, env=env, script=DELIVER)
                assert code == 0, err
                output = json.loads(out)
                specific = output["hookSpecificOutput"]
                assert specific["hookEventName"] == payload["hook_event_name"]
                for token in README_MARKS:
                    assert token in specific["additionalContext"], f"{label} never teaches {token}"
                assert "systemMessage" not in output, (
                    "a systemMessage prints the whole rule text into the user's transcript"
                )


class TheRuleTextTeachesTheMarksTheHooksEnforce(unittest.TestCase):
    def test_the_shipped_rule_text_and_the_hooks_name_the_same_four_marks(self) -> None:
        taught = set(MARK_SHAPED.findall(SHIPPED_RULE_BODY.read_text()))
        assert taught == README_MARKS, (
            f"the rule text teaches {sorted(taught)}, and the README names {sorted(README_MARKS)}"
        )
        assert set(MARKS) == README_MARKS, (
            f"the hooks enforce {sorted(MARKS)}, and the README names {sorted(README_MARKS)}"
        )


class TheWiringDeliversOnBothStarts(unittest.TestCase):
    def test_the_wiring_delivers_on_session_start_and_subagent_start(self) -> None:
        wiring = json.loads((PLUGIN_ROOT / "hooks" / "hooks.json").read_text())["hooks"]
        events = {
            event
            for event, matchers in wiring.items()
            for matcher in matchers
            for hook in matcher["hooks"]
            if "deliver-rule.py" in hook["command"]
        }
        assert events == {"SessionStart", "SubagentStart"}, (
            "delivery dropped on one start leaves that agent untaught"
        )


if __name__ == "__main__":
    unittest.main()
