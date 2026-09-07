"""Tests for flag-machine-prose.py, run from this directory:

    python3 -m pytest test_flag_machine_prose.py -v

Each test drives the script through stdin the way the harness does, with a
JSONL transcript written to a temporary file where the case needs one.
"""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).with_name("flag-machine-prose.py")


def entry(kind, content):
    return json.dumps({"type": kind, "message": {"role": kind, "content": content}})


def user_text(text):
    return entry("user", text)


def assistant_text(text):
    return entry("assistant", [{"type": "text", "text": text}])


def run_hook(payload):
    completed = subprocess.run(
        [sys.executable, str(SCRIPT)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        check=False,
    )
    return completed.returncode, completed.stdout


class FlagMachineProseStopHook(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)

    def transcript(self, *lines):
        path = Path(self._tmp.name) / "session.jsonl"
        path.write_text("\n".join(lines) + "\n")
        return str(path)

    def decision(self, message, **payload):
        code, out = run_hook(
            {"stop_hook_active": False, "last_assistant_message": message, **payload}
        )
        self.assertEqual(code, 0)
        return json.loads(out) if out.strip() else None

    def test_a_clean_reply_draws_no_output(self):
        self.assertIsNone(self.decision("The build passed on the second run."))

    def test_an_em_dash_blocks_and_the_reason_quotes_the_sentence_and_the_rule(self):
        result = self.decision("The build passed. The cache was cold — the run took longer.")
        self.assertIsNotNone(result, "an em dash must block the stop")
        self.assertEqual(result["decision"], "block")
        self.assertIn("The cache was cold — the run took longer.", result["reason"])
        self.assertNotIn("The build passed.", result["reason"].split("\n\n", 1)[1])
        self.assertIn("em dash", result["reason"])

    def test_a_spaced_en_dash_blocks_and_a_numeric_range_does_not(self):
        en_dash = chr(0x2013)
        self.assertIsNotNone(self.decision(f"The cache was cold {en_dash} the run took longer."))
        self.assertIsNone(self.decision(f"Lines 3{en_dash}5 hold the loop."))

    def test_a_rejecting_conjunction_blocks(self):
        for token in ("rather than", "instead of", "as opposed to"):
            result = self.decision(f"Use a period {token} a semicolon.")
            self.assertIsNotNone(result, f"{token!r} must block")
            self.assertIn("rejects an alternative", result["reason"])

    def test_a_mirror_opener_blocks(self):
        result = self.decision("The fix is not just a patch but a redesign.")
        self.assertIsNotNone(result)
        self.assertIn("mirror", result["reason"])

    def test_inflated_vocabulary_blocks_and_a_technical_noun_does_not(self):
        self.assertIsNotNone(self.decision("We can leverage the cache here."))
        self.assertIsNotNone(self.decision("The API is robust."))
        self.assertIsNone(self.decision("The paper measures robustness under noise."))

    def test_shape_as_a_generic_noun_blocks_and_the_verb_does_not(self):
        self.assertIsNotNone(self.decision("The shape of the response changed."))
        self.assertIsNone(self.decision("Each tradition reads as itself in the prose it shapes."))

    def test_load_bearing_blocks(self):
        self.assertIsNotNone(self.decision("That assumption is load-bearing."))

    def test_a_stock_opener_or_closer_blocks(self):
        self.assertIsNotNone(self.decision("Great question! The cache is cold."))
        self.assertIsNotNone(self.decision("Let me know if you want the diff."))
        self.assertIsNotNone(self.decision("I'll go ahead and run it."))

    def test_the_earning_idiom_blocks(self):
        result = self.decision("The helper earns its place in the module.")
        self.assertIsNotNone(result)
        self.assertIn("earns its place", result["reason"])

    def test_a_withheld_point_blocks(self):
        self.assertIsNotNone(self.decision("The catch: the cache never warms."))
        self.assertIsNotNone(self.decision("Here's the thing about caches."))

    def test_a_virtue_verdict_blocks(self):
        self.assertIsNotNone(self.decision("Honestly, the test covers it."))
        self.assertIsNotNone(self.decision("This is a genuine gap."))

    def test_a_hedge_standing_for_a_source_blocks(self):
        result = self.decision("As far as I know the flag defaults to off.")
        self.assertIsNotNone(result)
        self.assertIn("mark", result["reason"])

    def test_a_cushioning_hedge_blocks(self):
        self.assertIsNotNone(self.decision("It's worth noting the cache is cold."))
        self.assertIsNotNone(self.decision("It is important to note that the cache is cold."))

    def test_a_self_reference_blocks(self):
        self.assertIsNotNone(self.decision("As mentioned above, the cache is cold."))
        self.assertIsNotNone(self.decision("See below for the diff."))

    def test_a_strawman_opener_blocks(self):
        self.assertIsNotNone(self.decision("The fix is simpler than you might think."))
        self.assertIsNotNone(self.decision("Contrary to popular belief, the cache warms."))

    def test_an_emoji_blocks(self):
        self.assertIsNotNone(self.decision("Done ✅"))
        self.assertIsNotNone(self.decision("Shipped 🚀 to staging."))

    def test_a_tldr_blocks_on_a_short_message_and_stands_on_a_long_one(self):
        short = "TL;DR: the cache is cold.\n\nThe run took longer."
        self.assertIsNotNone(self.decision(short))
        long = "TL;DR: the cache is cold.\n\n" + " ".join(["word"] * 220)
        self.assertIsNone(self.decision(long))

    def test_a_flagged_string_inside_a_fenced_block_does_not_block(self):
        self.assertIsNone(self.decision("Here:\n```\nrather than — leverage\n```\nDone."))

    def test_a_flagged_string_inside_an_inline_code_span_does_not_block(self):
        self.assertIsNone(self.decision("The rule cuts `rather than` on sight."))

    def test_a_flagged_string_inside_double_quotation_marks_does_not_block(self):
        self.assertIsNone(self.decision('The author wrote "rather than" twice.'))
        self.assertIsNone(self.decision("The author wrote “rather than” twice."))

    def test_an_unclosed_quotation_mark_hides_nothing(self):
        result = self.decision('He opened a quote " and then wrote rather than here.')
        self.assertIsNotNone(result, "a quotation mark that never closes must exclude nothing")

    def test_a_flagged_string_outside_quotation_marks_on_a_line_that_also_quotes_one_blocks(self):
        result = self.decision('The rule names "rather than", and I would rather than not use it.')
        self.assertIsNotNone(result)

    def test_a_blockquote_line_does_not_block(self):
        self.assertIsNone(
            self.decision("> The cache was cold — the run took longer.\n\nQuoted above.")
        )

    def test_a_flagged_string_inside_a_url_does_not_block(self):
        self.assertIsNone(
            self.decision("See https://example.com/docs/leverage-and-robust for the API.")
        )

    def test_the_reason_groups_hits_under_the_rule_line_each_one_fails(self):
        result = self.decision(
            "Use a period rather than a semicolon. The cache was cold — it took longer."
        )
        reason = result["reason"]
        dash_rule = reason.index("em dash")
        rejection_rule = reason.index("rejects an alternative")
        dash_line = reason.index("The cache was cold — it took longer.")
        rejection_line = reason.index("Use a period rather than a semicolon.")
        self.assertLess(dash_rule, dash_line)
        self.assertLess(dash_line, rejection_rule)
        self.assertLess(rejection_rule, rejection_line)

    def test_the_reason_names_the_mention_escape(self):
        reason = self.decision("We can leverage the cache here.")["reason"]
        self.assertIn("quotation marks", reason)
        self.assertIn("backticks", reason)

    def test_the_reason_asks_for_the_reply_re_emitted_with_nothing_else_changed(self):
        reason = self.decision("We can leverage the cache here.")["reason"]
        self.assertIn("nothing else", reason)

    def test_earlier_text_of_the_same_turn_is_scanned_and_the_previous_turn_is_not(self):
        transcript = self.transcript(
            user_text("earlier question"),
            assistant_text("Old reply, we can leverage that."),
            user_text("do the thing"),
            assistant_text("The cache was cold — it took longer."),
        )
        result = self.decision("Done.", transcript_path=transcript)
        self.assertIsNotNone(result)
        self.assertIn("The cache was cold", result["reason"])
        self.assertNotIn("Old reply", result["reason"])

    def test_a_second_pass_reports_the_surviving_strings_without_blocking(self):
        result = self.decision("We can leverage the cache here.", stop_hook_active=True)
        self.assertIsNotNone(result, "a string that survived the pass reaches the user")
        self.assertNotIn("decision", result)
        self.assertIn("leverage", result["systemMessage"])

    def test_a_second_pass_stays_silent_when_no_string_survives(self):
        self.assertIsNone(self.decision("Every claim carries its source.", stop_hook_active=True))

    def test_the_hook_survives_an_unreadable_payload(self):
        completed = subprocess.run(
            [sys.executable, str(SCRIPT)],
            input="not json",
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 0)
        self.assertEqual(completed.stdout.strip(), "")


if __name__ == "__main__":
    unittest.main()
