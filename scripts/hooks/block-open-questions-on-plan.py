#!/usr/bin/env python3
"""Unified judge for ExitPlanMode plan bodies and Stop-event assistant
text. The body is sent to a local Ollama-served Qwen3 judge on every
invocation (no regex pre-filter). The judge fires one focused yes/no
call per verdict, in parallel; verdicts whose call returns `yes` are
collected into the block message.

Events handled:

- PreToolUse on `ExitPlanMode` — scan the plan body in `tool_input`.
- Stop / SubagentStop — scan the most recent assistant text in
  `transcript_path`.

Verdicts:

- EMPIRICAL_QUESTION — assistant asks the user something whose answer
  lives in documentation, types, logs, source, or an exploration the
  assistant could run themselves. The answer is a prerequisite the
  assistant should resolve, not a question for the user.
- OPEN_QUESTIONS — assistant asks the user a question that genuinely
  needs user input but writes it in inline prose instead of routing it
  through `AskUserQuestion`, or leaves placeholder tokens deferring a
  decision the assistant should have made.
- UNCOMMITTED_ALTERNATIVES — assistant lists two or more implementation
  paths and commits to none. Suppressed when `AskUserQuestion` was
  invoked in the same turn.
- OUT_OF_SCOPE_DEFERRAL — assistant sets aside a concrete failure (test,
  lint, build, type error, hook block, warning, diagnostic) as
  pre-existing, unrelated, not caused by this work, inherited, legacy,
  or otherwise not their responsibility — including by asking the user
  permission to leave it unfixed.
- BASELINE_PROBE — assistant proposes (or just performed) a comparison
  against the base branch (main, master, trunk) to determine whether a
  failure pre-exists.

The hook fails closed: if Ollama is unreachable, returns an
unrecognized response, or times out, the slim static reminder is
returned and the turn blocks. Set `BLOCK_PLAN_NO_JUDGE=1` to skip the
daemon call (and emit the same fallback message) — useful only when
diagnosing the daemon itself.
"""
import json
import os
import pathlib
import re
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

# Code stripping leaves the model judging the assistant's own prose,
# not strings or commands the assistant happened to echo back.
CODE_FENCE = re.compile(r"```[\s\S]*?```|~~~[\s\S]*?~~~")
INLINE_CODE = re.compile(r"`[^`\n]*`")

VERDICT_CLEAR = "CLEAR"
VERDICT_EMPIRICAL_QUESTION = "EMPIRICAL_QUESTION"
VERDICT_OPEN_QUESTIONS = "OPEN_QUESTIONS"
VERDICT_UNCOMMITTED_ALTERNATIVES = "UNCOMMITTED_ALTERNATIVES"
VERDICT_OUT_OF_SCOPE_DEFERRAL = "OUT_OF_SCOPE_DEFERRAL"
VERDICT_BASELINE_PROBE = "BASELINE_PROBE"
VALID_VERDICTS = {
    VERDICT_CLEAR,
    VERDICT_EMPIRICAL_QUESTION,
    VERDICT_OPEN_QUESTIONS,
    VERDICT_UNCOMMITTED_ALTERNATIVES,
    VERDICT_OUT_OF_SCOPE_DEFERRAL,
    VERDICT_BASELINE_PROBE,
}
# Tokens the model is allowed to emit. CLEAR is implicit — encoded by an
# empty `verdicts` array in the JSON response, never as a literal token.
EMITTABLE_VERDICTS = [
    VERDICT_EMPIRICAL_QUESTION,
    VERDICT_OPEN_QUESTIONS,
    VERDICT_UNCOMMITTED_ALTERNATIVES,
    VERDICT_OUT_OF_SCOPE_DEFERRAL,
    VERDICT_BASELINE_PROBE,
]

YES_NO_SCHEMA = {
    "type": "object",
    "properties": {"yes": {"type": "boolean"}},
    "required": ["yes"],
}

OLLAMA_URL = "http://localhost:11434/api/chat"
OLLAMA_MODEL = "qwen3:4b"
# Generous ceiling: the model must always run, so the timeout has to
# tolerate a cold load of the 2.5 GB weights to GPU memory after a
# reboot or after keep_alive expiry. Steady-state warm calls finish
# well under one second.
OLLAMA_TIMEOUT_SECONDS = 90
# Hold the model resident between hook invocations so most calls hit
# the warm path. Ollama parses Go-style duration strings.
OLLAMA_KEEP_ALIVE = "1h"
# Plan bodies and assistant turns are at most a few KB. The model's
# default 128k window allocates ~22 GB of GPU memory; 16k is more than
# enough for the largest plausible body plus the system prompt and
# verdict envelope, and shrinks the resident footprint substantially.
OLLAMA_NUM_CTX = 16384

# Each verdict is judged by its own focused yes/no call. The system
# prompt for each call answers one question. The model's output is
# schema-forced to {"yes": bool}; a `true` is a fired verdict.
#
# A verdict's question-form sentence is the natural yes-answer when
# read aloud: "Yes, this is an EMPIRICAL_QUESTION." Each spec is a
# (token, prompt) pair where the prompt fully scopes the decision.

_VERDICT_PROMPT_EMPIRICAL_QUESTION = (
    "Does the body contain a question the assistant directs at the "
    "user, where the answer would live in code, types, logs, source, "
    "or documentation that the assistant could fetch themselves?\n"
    "Genuine preference questions (\"do you want X or Y rolled out?\") "
    "are NOT empirical — answer no for those.\n"
    "Reporting, acknowledging, and explaining are not questions.\n\n"
    "Yes: \"What does the bun docs say about HMR?\"\n"
    "Yes: \"Should I import from `@foo/bar` or `foo/bar`?\"\n"
    "Yes: \"What type is the `request` parameter on the handler?\"\n"
    "No: \"Do you want this rolled out to all users or staff only?\"\n"
    "No: \"I added the helper at src/foo.ts.\"\n"
    "No: \"Tests pass and lint is clean.\""
)

_VERDICT_PROMPT_OPEN_QUESTIONS = (
    "Does the body contain a question the assistant directs at the "
    "user in inline prose (not routed through a structured "
    "AskUserQuestion tool), OR a placeholder marking an unresolved "
    "decision (TBD, TODO, FIXME, \"not sure\", \"unclear\", \"up to "
    "you\", \"your call\")?\n"
    "Reporting and acknowledging are not questions.\n\n"
    "Yes: \"Which approach do you prefer?\"\n"
    "Yes: \"Do you want this rolled out to all users or staff only?\"\n"
    "Yes: \"TODO: pick a name for this before merge.\"\n"
    "No: \"I went with option A — inlined the helper.\"\n"
    "No: \"Tests pass and lint is clean.\""
)

_VERDICT_PROMPT_UNCOMMITTED_ALTERNATIVES = (
    "Does the body enumerate two or more concrete implementation paths "
    "and commit to none of them?\n"
    "Triggers: \"two options\", \"A) … B) …\", \"either A or B\", \"we "
    "could … or …\", \"alternatively\". A clear pick (\"I went with "
    "A\") means no.\n"
    "A single TODO, naming decision, or open question is NOT "
    "alternatives — alternatives require two or more paths actually "
    "spelled out side by side. Answer no when there is only one path "
    "described.\n\n"
    "Yes: \"Two options: A) inline the helper, B) extract it into a "
    "module. Both have tradeoffs.\"\n"
    "Yes: \"Either we cache the response or we re-fetch each call — "
    "alternatively, we could memoize.\"\n"
    "No: \"I went with option A — inlined the helper.\"\n"
    "No: \"TODO: pick a name for this.\"\n"
    "No: \"Which approach do you prefer?\""
)

_VERDICT_PROMPT_OUT_OF_SCOPE_DEFERRAL = (
    "Does the body name a concrete failure (test failure, lint hit, "
    "build break, type diagnostic, hook block, warning) and set it "
    "aside as pre-existing, unrelated, inherited, legacy, "
    "out-of-scope, or otherwise not the assistant's responsibility "
    "to fix?\n"
    "Asking the user permission to leave the failure unfixed counts "
    "as a deferral attempt — answer yes for that.\n"
    "A clean report with no failures named (\"tests pass and lint is "
    "clean\") is not a deferral — answer no.\n\n"
    "Yes: \"Tests pass. The TS diagnostics are pre-existing, "
    "unrelated to my refactor.\"\n"
    "Yes: \"Tests pass. The TS errors are pre-existing. Should I "
    "leave them?\"\n"
    "Yes: \"The lint hits are inherited from before this work.\"\n"
    "No: \"Tests pass and lint is clean.\"\n"
    "No: \"I went with option A — inlined the helper.\""
)

_VERDICT_PROMPT_BASELINE_PROBE = (
    "Does the body propose or describe a comparison against the base "
    "branch (main, master, trunk) to determine whether a failure "
    "pre-exists?\n"
    "Includes: checking out the base branch, running tests on it, "
    "stashing local changes and switching to it.\n"
    "A plain rebase (\"I rebased onto main\") is NOT a probe — "
    "answer no for rebases.\n\n"
    "Yes: \"Let me check whether these tests fail on main.\"\n"
    "Yes: \"I'll stash my changes, switch to master, and run the "
    "suite to see if these failures pre-existed.\"\n"
    "Yes: \"Let me run the failing test against trunk.\"\n"
    "No: \"I rebased onto main and resolved the conflict.\"\n"
    "No: \"I merged main into the branch.\""
)

# Order matters only for the block message — verdicts list in this
# order when more than one fires.
VERDICT_SPECS = [
    (VERDICT_EMPIRICAL_QUESTION, _VERDICT_PROMPT_EMPIRICAL_QUESTION),
    (VERDICT_OPEN_QUESTIONS, _VERDICT_PROMPT_OPEN_QUESTIONS),
    (VERDICT_UNCOMMITTED_ALTERNATIVES, _VERDICT_PROMPT_UNCOMMITTED_ALTERNATIVES),
    (VERDICT_OUT_OF_SCOPE_DEFERRAL, _VERDICT_PROMPT_OUT_OF_SCOPE_DEFERRAL),
    (VERDICT_BASELINE_PROBE, _VERDICT_PROMPT_BASELINE_PROBE),
]

_FRAMING_PLAN = (
    "You judge an `ExitPlanMode` plan body for one specific issue. "
    "The body is between BEGIN and END markers.\n\n"
)

_FRAMING_STOP = (
    "You judge an assistant's turn-ending message for one specific "
    "issue. The body is between BEGIN and END markers.\n\n"
)

_OUTPUT_INSTRUCTION = (
    "\n\nOutput exactly `{\"yes\": true}` or `{\"yes\": false}`. "
    "JSON only, no prose."
)

# Quick-exit guard — if the body literally mentions any verdict token,
# the assistant is discussing the rules rather than breaking them. Skip
# the model entirely in that case.
_VERDICT_TOKENS_IN_BODY = re.compile(
    r"\b(EMPIRICAL_QUESTION|OPEN_QUESTIONS|UNCOMMITTED_ALTERNATIVES|"
    r"OUT_OF_SCOPE_DEFERRAL|BASELINE_PROBE)\b"
)

# Verdict glossary. Included verbatim in every block message so the
# assistant has the meanings on hand without depending on the system
# prompt context.
VERDICT_GLOSSARY = """EMPIRICAL_QUESTION — body asks the user something whose answer lives in documentation, types, logs, source, or an exploration the assistant could run.
OPEN_QUESTIONS — body asks the user a question that genuinely needs user input but in inline prose instead of `AskUserQuestion`, or carries placeholder tokens (TBD/TODO/FIXME/"not sure"/"unclear"/"up to you") deferring a decision.
UNCOMMITTED_ALTERNATIVES — body presents two or more implementation paths and commits to none.
OUT_OF_SCOPE_DEFERRAL — body sets aside a concrete failure (test, lint, build, type error, hook block, warning, diagnostic) as pre-existing, unrelated, inherited, legacy, or otherwise not the assistant's responsibility — including by asking permission to leave it unfixed.
BASELINE_PROBE — body proposes or performs a comparison against the base branch (main, master, trunk) to determine whether a failure pre-exists."""

_EMPIRICAL_REMEDIATION = """For any empirical question: stop asking and resolve it yourself. Spawn `Explore` for code, `general-purpose` with Tavily/Exa for web. Read the relevant types, logs, or source. Fold the answer in before you respond. The answer is a prerequisite, not a question for the user."""

_GENUINE_QUESTION_REMEDIATION = """For any question that genuinely depends on user preference: route it through `AskUserQuestion` with concrete options. Single question per call."""

_FAILURE_REMEDIATION = """For any failure flagged as pre-existing, unrelated, inherited, or out-of-scope: fix it. The answer to "should I leave it" is "no". Drop any baseline probe — the failure observed in the current work is the failure to fix, regardless of whether it also reproduces on main."""

_ALTERNATIVES_REMEDIATION = """For uncommitted alternatives: pick one and commit. State the tradeoff in one sentence so the discarded path is visible. If the choice genuinely needs the user's input, route it through `AskUserQuestion` instead of asking inline."""

REMEDIATION_PLAN = (
    "Re-read the plan and address each verdict before re-emitting "
    "`ExitPlanMode`.\n\n"
    + _EMPIRICAL_REMEDIATION + "\n\n"
    + _GENUINE_QUESTION_REMEDIATION + "\n\n"
    + _ALTERNATIVES_REMEDIATION + "\n\n"
    + _FAILURE_REMEDIATION
)

REMEDIATION_STOP = (
    "Re-read your message and address each verdict before ending the "
    "turn.\n\n"
    + _EMPIRICAL_REMEDIATION + "\n\n"
    + _GENUINE_QUESTION_REMEDIATION + "\n\n"
    + _ALTERNATIVES_REMEDIATION + "\n\n"
    + _FAILURE_REMEDIATION
)

ORIENTATION_PREFIX = "*\n\n"

FALLBACK_REPLAN_SLIM = """*

The local Ollama judge is unavailable. Re-read the body for: (1) direct questions to the user — route them through `AskUserQuestion`; (2) uncommitted alternatives — pick one and commit, or lift the choice into `AskUserQuestion`; (3) deterministic failures dismissed as out-of-scope, pre-existing, or unrelated — fix or request explicit per-failure permission to defer; (4) baseline probes against main/master/trunk to check whether a failure is pre-existing — skip the probe. Restart the Ollama daemon (`ollama serve`) before continuing. The judge runs on every turn now, so this hook fails closed when it cannot reach the model.
"""

LOG_PATH = pathlib.Path.home() / ".claude" / "logs" / "block-open-questions-on-plan.log"

EVENT_PLAN = "plan"
EVENT_STOP = "stop"


def _log_judge_call(event: str, duration_ms: int, verdicts: str) -> None:
    """Append one line per Ollama call so the user can `tail` real timings."""
    try:
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        with LOG_PATH.open("a", encoding="utf-8") as fh:
            fh.write(f"{ts}  event={event}  duration_ms={duration_ms}  verdicts={verdicts}\n")
    except OSError:
        pass


def _extract_plan(payload):
    ti = payload.get("tool_input", {})
    if not isinstance(ti, dict):
        return ""
    for key in ("plan", "content", "summary", "text", "body"):
        v = ti.get(key)
        if isinstance(v, str) and v.strip():
            return v
    parts = []
    for v in ti.values():
        if isinstance(v, str) and v.strip():
            parts.append(v)
    return "\n".join(parts)


def _read_transcript_lines(transcript_path: str) -> list[str]:
    if not transcript_path:
        return []
    try:
        with open(transcript_path, "r", encoding="utf-8") as fh:
            return fh.readlines()
    except OSError:
        return []


def last_assistant_text(transcript_path: str) -> str:
    """Return the most recent text-bearing assistant entry's text.

    A single assistant turn may produce multiple transcript entries
    (thinking / tool_use / text). We want the latest one with text;
    pure tool_use or thinking entries are skipped.
    """
    for raw in reversed(_read_transcript_lines(transcript_path)):
        raw = raw.strip()
        if not raw:
            continue
        try:
            entry = json.loads(raw)
        except ValueError:
            continue
        if entry.get("type") != "assistant":
            continue
        content = entry.get("message", {}).get("content", [])
        if isinstance(content, str):
            if content.strip():
                return content
            continue
        if isinstance(content, list):
            text = "\n".join(
                block.get("text", "")
                for block in content
                if isinstance(block, dict) and block.get("type") == "text"
            )
            if text.strip():
                return text
    return ""


def latest_turn_tool_uses(transcript_path: str) -> set[str]:
    """Return tool_use names from the latest turn (since the last user entry).

    Walks the transcript from the end. Stops at the first user entry,
    which marks the boundary of the current turn. Collects every
    tool_use block name found among assistant entries in between.
    """
    names: set[str] = set()
    for raw in reversed(_read_transcript_lines(transcript_path)):
        raw = raw.strip()
        if not raw:
            continue
        try:
            entry = json.loads(raw)
        except ValueError:
            continue
        et = entry.get("type")
        if et == "user":
            break
        if et != "assistant":
            continue
        content = entry.get("message", {}).get("content", [])
        if not isinstance(content, list):
            continue
        for block in content:
            if not isinstance(block, dict):
                continue
            if block.get("type") == "tool_use":
                name = block.get("name")
                if isinstance(name, str):
                    names.add(name)
    return names


def _strip_code(text: str) -> str:
    text = CODE_FENCE.sub("", text)
    text = INLINE_CODE.sub("", text)
    return text


_FIRED = "FIRED"
_NOT_FIRED = "NOT_FIRED"
_ERROR = "ERROR"


def _extract_yes(body) -> bool | None:
    """Pull the boolean from a yes/no /api/chat response.

    Schema-forced output is `{"yes": <bool>}`. Any deviation returns
    None so the caller treats the response as a judge failure and
    falls back closed.
    """
    if not isinstance(body, dict):
        return None
    message = body.get("message")
    if not isinstance(message, dict):
        return None
    content = message.get("content")
    if not isinstance(content, str) or not content.strip():
        return None
    try:
        parsed = json.loads(content)
    except ValueError:
        return None
    if not isinstance(parsed, dict):
        return None
    yes = parsed.get("yes")
    if not isinstance(yes, bool):
        return None
    return yes


def _judge_one(body_text: str, framing: str, verdict_prompt: str) -> bool | None:
    """One focused yes/no Ollama call. Returns True/False, or None on error.

    None signals an outage or malformed response — the caller treats
    that as a fail-closed signal across the whole judgment.
    """
    system_prompt = framing + verdict_prompt + _OUTPUT_INSTRUCTION
    framed = (
        "Below, between BEGIN and END markers, is the body to judge.\n\n"
        "===== BEGIN BODY =====\n"
        f"{body_text}\n"
        "===== END BODY =====\n"
    )

    payload = json.dumps(
        {
            "model": OLLAMA_MODEL,
            "stream": False,
            "think": False,
            "keep_alive": OLLAMA_KEEP_ALIVE,
            "format": YES_NO_SCHEMA,
            "options": {"num_ctx": OLLAMA_NUM_CTX},
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": framed},
            ],
        }
    ).encode("utf-8")

    request = urllib.request.Request(
        OLLAMA_URL,
        data=payload,
        method="POST",
        headers={"content-type": "application/json"},
    )

    try:
        with urllib.request.urlopen(request, timeout=OLLAMA_TIMEOUT_SECONDS) as resp:
            body = json.load(resp)
    except urllib.error.HTTPError:
        return None
    except (urllib.error.URLError, TimeoutError, OSError, ValueError):
        return None

    return _extract_yes(body)


def ollama_judge(body_text: str, framing: str, event: str) -> list[str] | None:
    """Run all five focused calls in parallel; return fired verdicts.

    Returns:
      - [VERDICT_CLEAR] when none fired (and quick-exit cases)
      - [verdicts...] when one or more fired
      - None when any call failed (fail-closed)

    Quick-exit: if the body literally contains a verdict token, the
    assistant is discussing the rules. Return clear without a model
    call.
    """
    if _VERDICT_TOKENS_IN_BODY.search(body_text):
        _log_judge_call(event, 0, f"{VERDICT_CLEAR}:quick-exit")
        return [VERDICT_CLEAR]

    started = time.monotonic()
    with ThreadPoolExecutor(max_workers=len(VERDICT_SPECS)) as pool:
        futures = {
            pool.submit(_judge_one, body_text, framing, prompt): name
            for name, prompt in VERDICT_SPECS
        }
        results: dict[str, bool | None] = {}
        for fut in futures:
            name = futures[fut]
            try:
                results[name] = fut.result()
            except Exception:
                results[name] = None
    elapsed_ms = int((time.monotonic() - started) * 1000)

    if any(v is None for v in results.values()):
        errored = [n for n, v in results.items() if v is None]
        _log_judge_call(event, elapsed_ms, f"{_ERROR}:{','.join(errored)}")
        return None

    fired = [name for name, _ in VERDICT_SPECS if results[name]]
    if not fired:
        _log_judge_call(event, elapsed_ms, VERDICT_CLEAR)
        return [VERDICT_CLEAR]
    _log_judge_call(event, elapsed_ms, ",".join(fired))
    return fired


def compose_message(verdicts: list[str], remediation: str) -> str:
    """Build the block message: orientation + verdicts + glossary + remediation.

    The mapping from verdict to canned remediation segment was removed
    intentionally. The model named the verdicts; we hand them through with
    the glossary and a short remediation paragraph and let the assistant
    figure out which lines apply. This keeps the hook from making a brittle
    deterministic bet on which canned paragraph fits which verdict.
    """
    if not verdicts:
        return ""
    listed = ", ".join(verdicts)
    return (
        ORIENTATION_PREFIX
        + f"Local Ollama judge fired: `{listed}`.\n\n"
        + VERDICT_GLOSSARY
        + "\n\n"
        + remediation
        + "\n"
    )


def emit_pretooluse_block(reason: str) -> None:
    json.dump(
        {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": reason,
            },
            "systemMessage": reason,
        },
        sys.stdout,
    )


def emit_stop_block(reason: str) -> None:
    json.dump(
        {"decision": "block", "reason": reason, "systemMessage": reason},
        sys.stdout,
    )


def _suppress_uncommitted_alternatives(verdicts: list[str], turn_tools: set[str]) -> list[str]:
    """Drop UNCOMMITTED_ALTERNATIVES if AskUserQuestion was invoked this turn.

    The whole point of UNCOMMITTED_ALTERNATIVES is to push the choice
    into `AskUserQuestion`. If that tool is already in flight this turn,
    the assistant is doing the right thing — don't block on it.
    """
    if "AskUserQuestion" not in turn_tools:
        return verdicts
    return [v for v in verdicts if v != VERDICT_UNCOMMITTED_ALTERNATIVES]


def _handle(body_text: str, transcript_path: str, event: str,
            framing: str, remediation: str) -> str | None:
    """Judge the body via Ollama and compose. Returns block text or None.

    Returns None to mean "do not block". Returns FALLBACK_REPLAN_SLIM
    when the judge is unreachable — the hook fails closed by design so
    that a daemon outage cannot silently disable the safety net.
    """
    if not body_text.strip():
        return None

    scrubbed = _strip_code(body_text)

    if os.environ.get("BLOCK_PLAN_NO_JUDGE") == "1":
        return FALLBACK_REPLAN_SLIM

    verdicts = ollama_judge(scrubbed, framing, event)
    if verdicts is None:
        return FALLBACK_REPLAN_SLIM

    if all(v == VERDICT_CLEAR for v in verdicts):
        return None

    verdicts = _suppress_uncommitted_alternatives(
        verdicts, latest_turn_tool_uses(transcript_path)
    )
    if not verdicts:
        return None

    message = compose_message(verdicts, remediation)
    return message or None


def main() -> None:
    try:
        payload = json.load(sys.stdin)
    except ValueError:
        sys.exit(0)

    transcript_path = payload.get("transcript_path", "") or ""

    if "tool_name" in payload:
        if payload.get("tool_name") != "ExitPlanMode":
            sys.exit(0)
        plan = _extract_plan(payload)
        message = _handle(
            plan, transcript_path, EVENT_PLAN,
            _FRAMING_PLAN, REMEDIATION_PLAN,
        )
        if message:
            emit_pretooluse_block(message)
        sys.exit(0)

    # Stop / SubagentStop have transcript_path but no tool_name.
    if transcript_path:
        text = last_assistant_text(transcript_path)
        message = _handle(
            text, transcript_path, EVENT_STOP,
            _FRAMING_STOP, REMEDIATION_STOP,
        )
        if message:
            emit_stop_block(message)
        sys.exit(0)

    sys.exit(0)


if __name__ == "__main__":
    main()
