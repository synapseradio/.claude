"""Tests for the strings the hooks generate, driven at the builders:

    python3.14 -m pytest tests/test_messages.py -v

Every other test module drives a hook through stdin, which is where behavior
lives. What is pinned here is the prose itself, so the assertions read the
builders' output directly rather than a payload's worth of it.
"""

import sys
import unittest
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PLUGIN_ROOT))

from epistemic_marks.marks import MARK_CARRY, MARK_RESOLVE, MARKS  # noqa: E402
from epistemic_marks.messages import (  # noqa: E402
    CITATION_HEADING,
    MENTION_HEADING,
    RELAY_HEADING,
    SURVIVING_HEADING,
    build_context,
    build_notice,
    build_reason,
)

# The tools a generated string reached for before the strip, standing here for
# every tool name. The reader runs on a machine whose toolset this plugin
# cannot know, so naming one asks for a call that may not exist.
TOOL_NAMES = ("Read", "Grep", "Glob", "AskUserQuestion", "linkup", "tavily", "context7")


class ADetectedMarkIsTheOnlyMarkThatPrints(unittest.TestCase):
    def test_a_lone_mark_draws_no_other_marks_glyph_or_instruction(self):
        for found in MARKS:
            with self.subTest(mark=found):
                output = build_reason({found: [f"A claim {found}."]})
                for other in MARKS:
                    if other == found:
                        continue
                    self.assertNotIn(
                        MARK_RESOLVE[other],
                        output,
                        f"a reply carrying {found} alone was told what to do about {other}",
                    )
                    self.assertNotIn(
                        f"\n{other}\n",
                        output,
                        f"{other} heads a subsection over lines that nobody wrote",
                    )


class NoGeneratedStringNamesATool(unittest.TestCase):
    """The output reaches an agent whose toolset this plugin cannot know.

    Asserting over the builders' output rather than the module source is what
    catches a tool name reintroduced through an f-string.
    """

    def every_mark(self):
        return {token: [f"A claim {token}."] for token in MARKS}

    def outputs(self):
        return {
            "reason": build_reason(self.every_mark(), self.every_mark(), delegate=True),
            "context": build_context(self.every_mark()),
            "notice": build_notice(
                self.every_mark(),
                self.every_mark(),
                {"beta.py": "beta.py:42"},
            ),
        }

    def test_no_builder_names_a_tool(self):
        for name, output in self.outputs().items():
            for tool in TOOL_NAMES:
                with self.subTest(builder=name, tool=tool):
                    self.assertNotIn(
                        tool,
                        output,
                        f"{name} asks for {tool}, which the reader's machine may not have",
                    )


class TheHeadingsStayDistinct(unittest.TestCase):
    def test_no_two_headings_share_their_text(self):
        headings = (RELAY_HEADING, SURVIVING_HEADING, MENTION_HEADING, CITATION_HEADING)
        self.assertEqual(
            len(set(headings)),
            len(headings),
            "two headings reading alike leave a reader unable to tell the groups apart, "
            "and a test anchored on one of them passing over the other",
        )


class EveryMarkCarriesBothActs(unittest.TestCase):
    def test_the_carry_act_differs_from_the_resolve_act(self):
        for token in MARKS:
            with self.subTest(mark=token):
                self.assertNotEqual(
                    MARK_RESOLVE[token],
                    MARK_CARRY[token],
                    f"{token} would be asked the same thing whether or not it can be "
                    "settled in this pass",
                )


if __name__ == "__main__":
    unittest.main()
