#!/usr/bin/env python3
"""PreToolUse hook on ExitPlanMode — block plans containing open questions
or uncommitted multi-path tradeoffs.

Reads stdin JSON {tool_name, tool_input}. When tool_name is "ExitPlanMode",
inspects the plan body (tool_input.plan / .content / .text, falling back to
all string values) for:

1. Direct interrogatives left to the user (Should we X? Which approach?
   What about Y?). These belong outside the plan body — research for
   empirical ones, AskUserQuestion for subjective ones.

2. Multi-path framing without a stated commitment ("Option A or Option B",
   "we could ... alternatively ..."). The plan is Claude's recommendation;
   a tradeoff that isn't picked is a deferral.

Code fences are stripped before scanning to avoid matching example syntax.

On detection, returns a deny decision via hookSpecificOutput plus a
systemMessage that instructs Claude to triage each question:

  - Empirical (codebase fact, lib behavior, doc lookup) → spawn Agent
    (Explore for code, general-purpose with web search for online).
  - Subjective / preference → emit AskUserQuestion calls.
  - Tradeoff between paths → pick one and commit; surface the tradeoff in
    one sentence inside the plan, not the choice.

Then resubmit ExitPlanMode.
"""
import json
import re
import sys

# Sentence-shaped questions that read as user-directed asks.
INTERROGATIVE = re.compile(
    r"\b(?:should|shall|do|does|will|would|can|could|might|may|"
    r"which|what|how|why|where|when|who)\b"
    r"[^.!?\n]{0,250}\?",
    re.IGNORECASE,
)

# Explicit placeholders that signal an unresolved item.
PLACEHOLDER = re.compile(
    r"\bTBD\b"
    r"|\bTODO\b\s*[:?]?"
    r"|\bopen question\b"
    r"|\bunresolved\b"
    r"|\bunknown\b\s*[:?]"
    r"|\bnot sure\b"
    r"|\bunclear\b",
    re.IGNORECASE,
)

# Multi-path framing — A vs B, options, alternatives.
ALTERNATIVES = re.compile(
    r"\boption\s+(?:a|b|c|d|1|2|3|4|one|two|three|four)\b"
    r"|\bapproach\s+(?:a|b|c|d|1|2|3|4|one|two|three|four)\b"
    r"|\bpath\s+(?:a|b|1|2|one|two)\b"
    r"|\b(?:option|approach|path)\s*[:#]\s*[a-z0-9]+\b"
    r"|\beither\b[^.!?\n]{0,80}\bor\b"
    r"|\bor (?:we|i|you) could\b"
    r"|\bcould (?:go|take|use|pick) (?:either|any|both)\b"
    r"|\b(?:two|three|several|multiple) (?:options|approaches|paths|choices|ways|directions)\b"
    r"|\balternatively\b",
    re.IGNORECASE,
)

# Commitment language — when present alongside ALTERNATIVES, the multi-path
# framing is a tradeoff explanation, not a deferral.
COMMITMENT = re.compile(
    r"\bi(?:'ll|'m|am| will| have| 'm)\s+(?:go(?:ing)?|chosen?|"
    r"select(?:ed|ing)?|pick(?:ed|ing)?|decid(?:ed|ing)?|"
    r"recommend(?:ing)?|propos(?:e|ing))\b"
    r"|\bgoing with\b"
    r"|\bdecision\s*[:\-]\s*"
    r"|\brecommended approach\b"
    r"|\bchosen approach\b"
    r"|\b(?:my|the)\s+(?:recommendation|choice|pick)\b"
    r"|\bi recommend\b"
    r"|\bi'?ll go with\b"
    r"|\bplan picks\b"
    r"|\b(?:choosing|picking|going|committing)\s+(?:option|approach|path)\b",
    re.IGNORECASE,
)

CODE_FENCE = re.compile(r"```[\s\S]*?```|~~~[\s\S]*?~~~")
INLINE_CODE = re.compile(r"`[^`\n]*`")

REPLAN = """*

YOUR PLAN CONTAINS OPEN QUESTIONS OR UNCOMMITTED ALTERNATIVES.
THIS BLOCKS PLAN SUBMISSION.

The plan body must not defer decisions back to the user implicitly.
Triage every open item BEFORE re-running ExitPlanMode:

1. EMPIRICAL questions (anything answerable by reading code, running a
   command, reading docs, or searching the web) — DO NOT ask the user.
   Spawn an agent to find the answer:
     - Codebase facts: subagent_type="Explore" (or general-purpose for
       deeper analysis). Hand it the exact question.
     - External facts (library behavior, API docs, web references):
       subagent_type="general-purpose" with explicit instruction to use
       Tavily / Exa (NEVER WebSearch / WebFetch — user policy).
   Wait for the agent's answer, fold it into the plan, then resubmit.

2. SUBJECTIVE / PREFERENCE questions (taste, scope priorities, UX choices,
   anything where the user's intent is the ground truth) — emit one or
   more AskUserQuestion calls BEFORE ExitPlanMode. One question per call;
   provide concrete options. Do not embed these questions in the plan
   body.

3. TRADEOFFS between paths ("Option A vs Option B", "we could ...
   alternatively ...") — pick one. State the tradeoff in a single
   sentence so the user can see the alternative was considered, then
   commit. The plan is your recommendation, not a menu.

After remediation, resubmit ExitPlanMode with all empirical questions
answered, all subjective questions surfaced via AskUserQuestion, and all
tradeoffs decided.
"""


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


def _strip_code(text: str) -> str:
    text = CODE_FENCE.sub("", text)
    text = INLINE_CODE.sub("", text)
    return text


def _has_open_question(text: str) -> bool:
    return bool(INTERROGATIVE.search(text)) or bool(PLACEHOLDER.search(text))


def _has_uncommitted_alternatives(text: str) -> bool:
    if not ALTERNATIVES.search(text):
        return False
    return not COMMITMENT.search(text)


def main() -> None:
    try:
        payload = json.load(sys.stdin)
    except ValueError:
        sys.exit(0)

    if payload.get("tool_name") != "ExitPlanMode":
        sys.exit(0)

    plan = _extract_plan(payload)
    if not plan:
        sys.exit(0)

    scrubbed = _strip_code(plan)
    triggered = (
        _has_open_question(scrubbed)
        or _has_uncommitted_alternatives(scrubbed)
    )
    if not triggered:
        sys.exit(0)

    json.dump(
        {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": REPLAN,
            },
            "systemMessage": REPLAN,
        },
        sys.stdout,
    )
    sys.exit(0)


if __name__ == "__main__":
    main()
