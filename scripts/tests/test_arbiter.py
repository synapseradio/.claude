#!/usr/bin/env python3
"""Offline tests for Arbiter — loader, dispatch pipeline, and the
Stop-misfire lockin.

These do not need a running llama-server. Run with `python3
test_arbiter.py`. Exits non-zero on any failure.

Coverage:
- YAML loader on valid bindings.yaml
- YAML loader on a corpus of invalid fixtures (parse errors, missing
  fields, unknown refs, mismatched (event, action) pairs)
- Dispatch pipeline with the client mocked, exercising the four
  message-shape combinations (deny / block / fallback-deny /
  fallback-block)
- Composer parity: a representative multi-verdict combination per
  binding, asserting orientation, fired list, glossary scoping, and
  remediation scoping
- Stop / SubagentStop bindings never list `uncommitted_alternatives`
  — locks in the immediate concern that motivated the rewrite
"""

import io
import json
import pathlib
import sys
import tempfile

ARBITER_DIR = pathlib.Path(__file__).resolve().parents[1] / "arbiter"
sys.path.insert(0, str(ARBITER_DIR))

from lib import dispatcher  # noqa: E402
from lib.compose import FALLBACK_REPLAN_SLIM, compose_message  # noqa: E402
from lib.config import ConfigError, load_bindings  # noqa: E402

BINDINGS_PATH = ARBITER_DIR / "bindings.yaml"

PASS = 0
FAIL = 0


def _ok(name: str) -> None:
    global PASS
    PASS += 1
    print(f"  PASS  {name}")


def _fail(name: str, msg: str) -> None:
    global FAIL
    FAIL += 1
    print(f"  FAIL  {name}: {msg}")


def _section(label: str) -> None:
    print(f"\n[{label}]")


def test_loader_valid():
    """The shipped bindings.yaml loads cleanly and exposes every verdict."""
    b = load_bindings(BINDINGS_PATH)
    expected = {
        "open_questions",
        "empirical_question",
        "uncommitted_alternatives",
        "out_of_scope_deferral",
        "baseline_probe",
    }
    if set(b.verdicts) != expected:
        _fail("loader_valid", f"verdicts {set(b.verdicts)} != {expected}")
        return
    if set(b.remediation) != {"question", "alternatives", "failure", "empirical"}:
        _fail("loader_valid", f"remediation keys {set(b.remediation)} unexpected")
        return
    if len(b.bindings) != 3:
        _fail("loader_valid", f"expected 3 bindings, got {len(b.bindings)}")
        return
    _ok("loader_valid")


def test_loader_invalid():
    """Each invalid YAML class produces a ConfigError with file:line:col."""
    cases = [
        ("missing-verdicts", "bindings: []\n"),
        ("missing-bindings", "verdicts: {}\n"),
        (
            "unknown-action",
            """verdicts:
  open_questions:
    prompt: hi
    glossary: hi
    remediation: []
remediation: {}
bindings:
  - event: PreToolUse
    tool: ExitPlanMode
    verdicts: [open_questions]
    action: nuke
""",
        ),
        (
            "mismatched-event-action",
            """verdicts:
  open_questions:
    prompt: hi
    glossary: hi
    remediation: []
remediation: {}
bindings:
  - event: Stop
    verdicts: [open_questions]
    action: ask
""",
        ),
        (
            "unknown-verdict-ref",
            """verdicts:
  open_questions:
    prompt: hi
    glossary: hi
    remediation: []
remediation: {}
bindings:
  - event: PreToolUse
    tool: ExitPlanMode
    verdicts: [does_not_exist]
    action: deny
""",
        ),
        (
            "unknown-remediation-key",
            """verdicts:
  open_questions:
    prompt: hi
    glossary: hi
    remediation: [missing_key]
remediation: {}
bindings:
  - event: PreToolUse
    tool: ExitPlanMode
    verdicts: [open_questions]
    action: deny
""",
        ),
        (
            "unknown-field",
            """verdicts:
  open_questions:
    prompt: hi
    glossary: hi
    remediation: []
    bogus: yes
remediation: {}
bindings:
  - event: PreToolUse
    tool: ExitPlanMode
    verdicts: [open_questions]
    action: deny
""",
        ),
    ]
    for label, content in cases:
        path = pathlib.Path(tempfile.mkstemp(suffix=".yaml")[1])
        path.write_text(content)
        try:
            try:
                load_bindings(path)
                _fail(f"loader_invalid:{label}", "expected ConfigError, got success")
            except ConfigError as exc:
                msg = str(exc)
                # Located message format: <path>:<line>:<col>: <text> OR <path>: <text>
                if not msg.startswith(str(path)):
                    _fail(f"loader_invalid:{label}", f"message missing source path: {msg}")
                else:
                    _ok(f"loader_invalid:{label}")
        finally:
            path.unlink()


def test_stop_misfire_lockin():
    """Stop / SubagentStop bindings subscribe the full predecessor-coverage set.

    The predecessor `block-open-questions-on-plan.py` ran five verdicts on
    every Stop event. The declarative engine must keep parity on the four
    user-locked verdicts plus `empirical_question`, which the user decided
    runs on turn_review only.
    """
    required = {
        "empirical_question",
        "open_questions",
        "uncommitted_alternatives",
        "out_of_scope_deferral",
        "baseline_probe",
    }
    b = load_bindings(BINDINGS_PATH)
    for entry in b.bindings:
        if entry.event in ("Stop", "SubagentStop"):
            missing = required - set(entry.verdict_ids)
            if missing:
                _fail(
                    "stop_misfire_lockin",
                    f"{entry.event} binding missing required verdicts: {sorted(missing)}",
                )
                return
    _ok("stop_misfire_lockin")


def test_compose_scoping():
    """Composer emits glossary + remediation scoped to fired verdicts only."""
    b = load_bindings(BINDINGS_PATH)
    fired = [b.verdicts["open_questions"], b.verdicts["baseline_probe"]]
    msg = compose_message(fired, b.remediation, "Stop")

    if not msg.startswith("*\n\n"):
        _fail("compose_scoping", "missing orientation prefix")
        return
    if "OPEN_QUESTIONS, BASELINE_PROBE" not in msg:
        _fail("compose_scoping", "fired list not in message")
        return
    # Glossary scoping: UNCOMMITTED_ALTERNATIVES and OUT_OF_SCOPE_DEFERRAL
    # glossary lines must NOT appear when only OPEN_QUESTIONS + BASELINE_PROBE fired.
    if "UNCOMMITTED_ALTERNATIVES — body presents" in msg:
        _fail("compose_scoping", "non-fired UNCOMMITTED_ALTERNATIVES glossary leaked in")
        return
    if "OUT_OF_SCOPE_DEFERRAL — body sets aside" in msg:
        _fail("compose_scoping", "non-fired OUT_OF_SCOPE_DEFERRAL glossary leaked in")
        return
    # Remediation scoping: open_questions → question, baseline_probe → failure.
    # The "alternatives" paragraph must not appear.
    if "For uncommitted alternatives:" in msg:
        _fail("compose_scoping", "non-referenced alternatives remediation leaked in")
        return
    if "The plan file seems to include questions to the user." not in msg:
        _fail("compose_scoping", "question remediation missing")
        return
    if "A failure was named and set aside as pre-existing" not in msg:
        _fail("compose_scoping", "failure remediation missing")
        return
    if "A second look at the closing message before ending the turn:" not in msg:
        _fail("compose_scoping", "Stop remediation lead missing")
        return
    _ok("compose_scoping")


def test_compose_plan_event_lead():
    """Plan binding gets the plan-event lead, not the turn-event lead."""
    b = load_bindings(BINDINGS_PATH)
    fired = [b.verdicts["open_questions"]]
    msg = compose_message(fired, b.remediation, "PreToolUse")
    if "A second look at the plan before re-emitting ExitPlanMode:" not in msg:
        _fail("compose_plan_lead", "plan-event lead missing")
        return
    if "A second look at the closing message before ending the turn:" in msg:
        _fail("compose_plan_lead", "turn-event lead leaked into plan message")
        return
    _ok("compose_plan_lead")


def _patch_judge_many(monkey_result):
    """Replace dispatcher.client.judge_many with a stub that returns
    `monkey_result`. Returns the original for restore."""
    original = dispatcher.client.judge_many

    def _stub(body_text, framing, verdict_specs, event):
        if monkey_result == "ALL":
            return [s.key for s in verdict_specs]
        if monkey_result == "ERROR":
            return None
        if monkey_result == "NONE":
            return []
        # Otherwise, list of verdict keys to fire.
        keys = set(monkey_result)
        return [s.key for s in verdict_specs if s.key in keys]

    dispatcher.client.judge_many = _stub
    return original


def _restore_judge_many(original):
    dispatcher.client.judge_many = original


def _reset_cache():
    dispatcher._CACHED_BINDINGS = None


def test_dispatch_pretooluse_deny():
    """PreToolUse:ExitPlanMode emits a deny shape when verdicts fire."""
    _reset_cache()
    original = _patch_judge_many({"open_questions"})
    try:
        out = io.StringIO()
        dispatcher.dispatch(
            {
                "hook_event_name": "PreToolUse",
                "tool_name": "ExitPlanMode",
                "tool_input": {"plan": "Should I do A or B? Let me know."},
            },
            out,
        )
        result = json.loads(out.getvalue())
        if result["hookSpecificOutput"]["hookEventName"] != "PreToolUse":
            _fail("dispatch_pretooluse_deny", "wrong hookEventName")
            return
        if result["hookSpecificOutput"]["permissionDecision"] != "deny":
            _fail("dispatch_pretooluse_deny", "wrong permissionDecision")
            return
        reason = result["hookSpecificOutput"]["permissionDecisionReason"]
        if "OPEN_QUESTIONS" not in reason:
            _fail("dispatch_pretooluse_deny", "fired verdict not in reason")
            return
        _ok("dispatch_pretooluse_deny")
    finally:
        _restore_judge_many(original)


def test_dispatch_stop_block():
    """Stop emits a block shape when verdicts fire."""
    _reset_cache()
    original = _patch_judge_many({"out_of_scope_deferral"})
    try:
        # Synthetic transcript: latest assistant entry has text.
        with tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False) as fh:
            fh.write(
                json.dumps(
                    {
                        "type": "assistant",
                        "message": {
                            "content": [
                                {
                                    "type": "text",
                                    "text": "Tests pass. The TS errors are pre-existing.",
                                }
                            ]
                        },
                    }
                )
                + "\n"
            )
            transcript = fh.name
        out = io.StringIO()
        dispatcher.dispatch(
            {"hook_event_name": "Stop", "transcript_path": transcript},
            out,
        )
        result = json.loads(out.getvalue())
        if result.get("decision") != "block":
            _fail("dispatch_stop_block", f"wrong decision: {result}")
            return
        if "OUT_OF_SCOPE_DEFERRAL" not in result.get("reason", ""):
            _fail("dispatch_stop_block", "fired verdict not in reason")
            return
        _ok("dispatch_stop_block")
    finally:
        _restore_judge_many(original)


def test_dispatch_judge_unreachable():
    """Judge error → fallback message via the binding's action shape."""
    _reset_cache()
    original = _patch_judge_many("ERROR")
    try:
        out = io.StringIO()
        dispatcher.dispatch(
            {
                "hook_event_name": "PreToolUse",
                "tool_name": "ExitPlanMode",
                "tool_input": {"plan": "All paths lead to Rome. Should we go A or B?"},
            },
            out,
        )
        result = json.loads(out.getvalue())
        if result["hookSpecificOutput"]["permissionDecision"] != "deny":
            _fail("dispatch_judge_unreachable", "missing deny shape")
            return
        if result["hookSpecificOutput"]["permissionDecisionReason"] != FALLBACK_REPLAN_SLIM:
            _fail("dispatch_judge_unreachable", "fallback text mismatch")
            return
        _ok("dispatch_judge_unreachable")
    finally:
        _restore_judge_many(original)


def test_dispatch_clear_emits_nothing():
    """No fired verdicts → no JSON emitted."""
    _reset_cache()
    original = _patch_judge_many("NONE")
    try:
        out = io.StringIO()
        dispatcher.dispatch(
            {
                "hook_event_name": "PreToolUse",
                "tool_name": "ExitPlanMode",
                "tool_input": {"plan": "Tests pass and lint is clean."},
            },
            out,
        )
        if out.getvalue() != "":
            _fail("dispatch_clear_emits_nothing", f"unexpected output: {out.getvalue()!r}")
            return
        _ok("dispatch_clear_emits_nothing")
    finally:
        _restore_judge_many(original)


def test_dispatch_unknown_event_no_op():
    """A hook event with no binding emits nothing (silent pass-through)."""
    _reset_cache()
    out = io.StringIO()
    dispatcher.dispatch({"hook_event_name": "Notification"}, out)
    if out.getvalue() != "":
        _fail("dispatch_unknown_event_no_op", f"unexpected output: {out.getvalue()!r}")
        return
    _ok("dispatch_unknown_event_no_op")


def test_dispatch_suppression_drops_uncommitted():
    """uncommitted_alternatives is dropped when AskUserQuestion is in the
    latest turn — even on PreToolUse, where the binding subscribes it."""
    _reset_cache()
    original = _patch_judge_many({"uncommitted_alternatives"})
    try:
        with tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False) as fh:
            fh.write(
                json.dumps(
                    {
                        "type": "user",
                        "message": {"content": [{"type": "text", "text": "go"}]},
                    }
                )
                + "\n"
            )
            fh.write(
                json.dumps(
                    {
                        "type": "assistant",
                        "message": {
                            "content": [
                                {"type": "tool_use", "name": "AskUserQuestion", "input": {}},
                            ]
                        },
                    }
                )
                + "\n"
            )
            transcript = fh.name
        out = io.StringIO()
        dispatcher.dispatch(
            {
                "hook_event_name": "PreToolUse",
                "tool_name": "ExitPlanMode",
                "transcript_path": transcript,
                "tool_input": {"plan": "Two options: A or B. Both have tradeoffs."},
            },
            out,
        )
        if out.getvalue() != "":
            _fail("dispatch_suppression", f"expected suppression, got output: {out.getvalue()!r}")
            return
        _ok("dispatch_suppression")
    finally:
        _restore_judge_many(original)


def main():
    _section("loader")
    test_loader_valid()
    test_loader_invalid()

    _section("composer")
    test_compose_scoping()
    test_compose_plan_event_lead()

    _section("dispatch")
    test_dispatch_pretooluse_deny()
    test_dispatch_stop_block()
    test_dispatch_judge_unreachable()
    test_dispatch_clear_emits_nothing()
    test_dispatch_unknown_event_no_op()
    test_dispatch_suppression_drops_uncommitted()

    _section("lockin")
    test_stop_misfire_lockin()

    print(f"\n{PASS} passed, {FAIL} failed")
    sys.exit(1 if FAIL else 0)


if __name__ == "__main__":
    main()
