"""Tests for the denied-route check of the verify-marks Stop pass, run from the plugin root.

    python3 -m unittest discover -s tests -p test_denied_route.py -v

The story: an agent's fetch for a source is denied by a permission check, and
the agent marks the claim in place of the source without trying another
route. The reply is sent back until another route is tried. Each test builds
its transcript and state directory in a temporary directory under an
isolated HOME.
"""

import tempfile
import unittest
from pathlib import Path

from support import (
    assistant_text,
    entry,
    hook_output,
    isolated_environment,
    required,
    run_hook,
    user_text,
)

from epistemic_marks.messages import DENIED_ROUTE_HEADING

CURL = "curl -sfL 'https://docs.example.org/llms.txt' | head -60"
CLASSIFIER_DENIAL = "Permission for this action was denied by the Claude Code auto mode classifier."
USER_REFUSAL = "The user doesn't want to proceed with this tool use. The tool use was rejected."
MARKED_REPLY = "The bundled docs may lag the live site [?]."


def tool_use(call_id, name, tool_input) -> str:
    return entry(
        "assistant", [{"type": "tool_use", "id": call_id, "name": name, "input": tool_input}]
    )


def tool_result(call_id, content, *, is_error=False) -> str:
    return entry(
        "user",
        [{"type": "tool_result", "tool_use_id": call_id, "content": content, "is_error": is_error}],
    )


class DeniedRoute(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        root = Path(self._tmp.name)
        self.env = isolated_environment(root / "home", state_dir=root / "state")

    def transcript(self, *lines) -> str:
        path = Path(self._tmp.name) / "session.jsonl"
        path.write_text("\n".join(lines) + "\n")
        return str(path)

    def stop(self, payload) -> dict | None:
        code, out, err = run_hook(payload, env=self.env)
        assert code == 0, err
        return hook_output(out)

    def denied_curl(self, *after) -> str:
        return self.transcript(
            user_text("what does the docs site say about hooks?"),
            tool_use("t1", "Bash", {"command": CURL}),
            tool_result("t1", CLASSIFIER_DENIAL, is_error=True),
            *after,
        )

    def test_a_mark_after_a_denied_fetch_with_no_other_route_blocks_and_names_the_fetch(
        self,
    ) -> None:
        transcript = self.denied_curl()
        result = required(
            self.stop(
                {
                    "stop_hook_active": False,
                    "transcript_path": transcript,
                    "last_assistant_message": MARKED_REPLY,
                }
            )
        )
        assert result["decision"] == "block"
        assert DENIED_ROUTE_HEADING in result["reason"]
        assert f"- {CURL}" in result["reason"], "the reader needs the route that was denied"

    def test_another_fetch_after_the_denial_ends_the_finding(self) -> None:
        transcript = self.denied_curl(
            tool_use(
                "t2", "mcp__tavily__tavily_extract", {"urls": ["https://docs.example.org/llms.txt"]}
            ),
            tool_result("t2", "# Docs\nHooks run on events."),
        )
        result = self.stop(
            {
                "stop_hook_active": False,
                "transcript_path": transcript,
                "last_assistant_message": "Hooks run on events, per https://docs.example.org/llms.txt",
            }
        )
        assert result is None, "a second route tried and a sourced reply draw nothing"

    def test_a_later_pass_still_blocks_while_no_other_route_was_tried(self) -> None:
        transcript = self.denied_curl()
        payload = {"transcript_path": transcript, "session_id": "session-one"}
        self.stop({**payload, "stop_hook_active": False, "last_assistant_message": MARKED_REPLY})
        result = required(
            self.stop({**payload, "stop_hook_active": True, "last_assistant_message": MARKED_REPLY})
        )
        assert result["decision"] == "block", (
            "a reply that reopens on the mark has still tried no other route"
        )
        assert DENIED_ROUTE_HEADING in result["reason"]

    def test_a_persons_refusal_draws_no_route_finding(self) -> None:
        transcript = self.transcript(
            user_text("what does the docs site say about hooks?"),
            tool_use("t1", "Bash", {"command": CURL}),
            tool_result("t1", USER_REFUSAL, is_error=True),
            assistant_text(MARKED_REPLY),
        )
        result = required(
            self.stop(
                {
                    "stop_hook_active": False,
                    "transcript_path": transcript,
                    "last_assistant_message": MARKED_REPLY,
                }
            )
        )
        assert DENIED_ROUTE_HEADING not in result["reason"], (
            "a person's no is never a route to get around"
        )


if __name__ == "__main__":
    unittest.main()
