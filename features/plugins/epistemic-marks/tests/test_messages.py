"""Tests for the strings the hooks generate, driven at the builders.

    python3 -m unittest discover -s tests -p test_messages.py -v

Every other test module drives a hook through stdin, which is where behavior
lives. What is pinned here is the prose itself, so the assertions read the
builders' output directly rather than a payload's worth of it.
"""

import unittest

from epistemic_marks.marks import MARK_CARRY, MARK_RESOLVE, MARKS
from epistemic_marks.messages import (
    MENTION_ACT,
    MENTION_HEADING,
    RELAY_HEADING,
    SURVIVING_HEADING,
    Mode,
    build_context,
    build_findings,
)

# The tools a generated string reached for before the strip, standing here for
# every tool name. The reader runs on a machine whose toolset this plugin
# cannot know, so naming one asks for a call that may not exist.
TOOL_NAMES = ("Read", "Grep", "Glob", "AskUserQuestion", "linkup", "tavily", "context7")


class ADetectedMarkIsTheOnlyMarkThatPrints(unittest.TestCase):
    def test_a_lone_mark_draws_no_other_marks_glyph_or_instruction(self) -> None:
        for found in MARKS:
            with self.subTest(mark=found):
                output = build_findings(Mode.BLOCK, {found: [f"A claim {found}."]})
                for other in MARKS:
                    if other == found:
                        continue
                    assert MARK_RESOLVE[other] not in output, (
                        f"a reply carrying {found} alone was told what to do about {other}"
                    )
                    assert f"\n{other}\n" not in output, (
                        f"{other} heads a subsection over lines that nobody wrote"
                    )


class NoGeneratedStringNamesATool(unittest.TestCase):
    """The output reaches an agent whose toolset this plugin cannot know.

    Asserting over the builders' output rather than the module source is what
    catches a tool name reintroduced through an f-string.
    """

    def every_mark(self) -> dict[str, list[str]]:
        return {token: [f"A claim {token}."] for token in MARKS}

    def outputs(self) -> dict[str, str]:
        return {
            "reason": build_findings(
                Mode.BLOCK, self.every_mark(), self.every_mark(), delegate=True
            ),
            "context": build_context(self.every_mark()),
            "notice": build_findings(
                Mode.NOTICE,
                self.every_mark(),
                carried=self.every_mark(),
                mentions=self.every_mark(),
            ),
        }

    def test_no_builder_names_a_tool(self) -> None:
        for name, output in self.outputs().items():
            for tool in TOOL_NAMES:
                with self.subTest(builder=name, tool=tool):
                    assert tool not in output, (
                        f"{name} asks for {tool}, which the reader's machine may not have"
                    )


class EveryGroupAnAgentReadsCarriesAnAct(unittest.TestCase):
    """A notice reaches a delegate that can still act, so no group is a bare list."""

    def test_a_surviving_mark_is_listed_under_its_carry_act(self) -> None:
        for token in MARKS:
            with self.subTest(mark=token):
                notice = build_findings(Mode.NOTICE, {token: [f"A claim {token}."]})
                assert f"{token}\n{MARK_CARRY[token]}\n- A claim {token}." in notice, (
                    f"a surviving {token} reached the reader with nothing to do about it"
                )

    def test_a_mention_group_says_what_to_check(self) -> None:
        notice = build_findings(
            Mode.NOTICE, {}, mentions={"[?]": ["The unsourced mark, `[?]`, is named."]}
        )
        assert f"{MENTION_HEADING}\n{MENTION_ACT}\n" in notice, (
            "a mention passes unchecked, so the writer is the one left to check it"
        )


class TheHeadingsStayDistinct(unittest.TestCase):
    def test_no_two_headings_share_their_text(self) -> None:
        headings = (RELAY_HEADING, SURVIVING_HEADING, MENTION_HEADING)
        assert len(set(headings)) == len(headings), (
            "two headings reading alike leave a reader unable to tell the groups apart, "
            "and a test anchored on one of them passing over the other"
        )


class EveryMarkCarriesBothActs(unittest.TestCase):
    def test_the_carry_act_differs_from_the_resolve_act(self) -> None:
        for token in MARKS:
            with self.subTest(mark=token):
                assert MARK_RESOLVE[token] != MARK_CARRY[token], (
                    f"{token} would be asked the same thing whether or not it can be "
                    "settled in this pass"
                )


if __name__ == "__main__":
    unittest.main()
