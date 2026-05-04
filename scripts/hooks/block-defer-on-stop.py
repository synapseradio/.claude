#!/usr/bin/env python3
"""Stop-hook guard against deferral of deterministic failure signals.

Reads stdin JSON {transcript_path}. Inspects the most recent assistant turn.
If it contains language that minimizes failures (tests, lint, hooks, build),
emits a Stop block decision instructing the model to remediate immediately.

Two detection layers:

1. PHRASE_PATTERN — single phrases that are deferral on their face.
2. Combination rule — any sentence containing >= 2 words from
   {failure(s), fail(ed|ing|s), unrelated, scope(d), this} is treated as
   suspect. "this" alone is too common; pairings are the smell.
"""
import json
import re
import sys

# Single phrases that are deferral on their face — any one match triggers.
PHRASE_PATTERN = re.compile(
    r"out[- ]?of[- ]?scope"
    r"|outside (?:the |of )?scope"
    r"|not in scope"
    r"|n'?t in scope"
    r"|in[- ]?scope (?:for|of) (?:this|the|my|our)"
    r"|pre[- ]?existing"
    r"|preexisting"
    r"|unrelated to"
    r"|unrelated (?:failure|failures|test|tests|issue|issues|hang|hangs|problem|problems|item|items|thing|things|bug|bugs)"
    r"|(?:not |n'?t )(?:related|relevant) to"
    r"|deferring\s+\d"
    r"|defer (?:this|these|those|the|several|all|both|other|the rest)"
    r"|(?:carry|carried)[- ]?over"
    r"|carryover"
    r"|already (?:broken|failing|red|hung|hanging)"
    r"|(?:was|were|is|are) already (?:broken|failing|red)"
    r"|before this (?:session|task|plan|change|fix|work|run)"
    r"|predates? (?:this|the|my|our)"
    r"|pre[- ]?dates? (?:this|the|my|our)"
    r"|untouched by (?:my|this|the)"
    r"|separate (?:issue|problem|bug|failure|concern) from"
    r"|(?:doesn'?t|does not) (?:relate|touch|affect|involve|stem from) (?:my|this|the)"
    r"|not (?:my|mine|caused|introduced) by"
    r"|nothing to do with (?:my|this|the)"
    r"|to my changes"
    r"|orthogonal to (?:my|this|the)"
    r"|on (?:main|master|trunk) before (?:this|i |we |my |our )"
    r"|(?:red|failing|broken|hung|failed) on (?:main|master|trunk)"
    r"|present on (?:main|master|trunk)"
    r"|already on (?:main|master|trunk)"
    r"|inherited (?:failure|red|breakage)"
    r"|(?:failure|failures|tests?|hangs?|red|breakage) inherited from"
    r"|legacy (?:failure|test|red)"
    r"|fail(?:ed|ing|s|ure|ures)? .{0,40}? (?:before|on) (?:main|master|trunk)"
    r"|skip (?:this|that|those|these) (?:test|check|hook)",
    re.IGNORECASE,
)

# Words whose co-occurrence in a sentence forms the user's banned pattern.
# A pair (or more) of these in a single sentence triggers a block.
# "this" alone is benign — only counts when paired with a non-"this" hit.
COMBO_TOKENS = {
    "failure", "failures", "fail", "fails", "failed", "failing",
    "unrelated", "scope", "scoped", "this",
}

# Tokens that, when paired with "this", indicate failure-minimization.
# Restricted to failure-adjacent terms; high-collision idioms like
# "this work", "this plan", "this session", "this task", "this branch",
# "this PR", "this issue", "this concern" were dropped because they fire
# constantly in benign reference and overwhelm the signal.
THIS_PARTNERS = {
    "failure", "failures", "fail", "fails", "failed", "failing",
    "unrelated", "scope", "scoped",
}

REPLAN = """*

Your last message contains language the deferral guard flags as
minimizing a deterministic failure (test, lint, hook, build). Two paths:

If you are deferring a real failure — correct course:
  1. Enter plan mode.
  2. List each failure concretely; describe what is red and why.
  3. For each, propose either (a) fix now, or (b) ask explicit
     permission to defer (and name where it will be tracked).
  4. Surface the plan via ExitPlanMode and wait for approval.
  5. Resume only after approval; stop only after every item is
     fixed or explicitly authorized.

If this is a false positive — and only if you are confident the
language flagged was about something other than deferring a real
failure — say so to the user in one short sentence (quote the
phrase that tripped the guard) and ask whether to proceed.
"""


def last_assistant_text(transcript_path: str) -> str:
    """Return the most recent text-bearing assistant entry's text.

    A single assistant turn may produce multiple transcript entries
    (thinking / tool_use / text). We want the latest one with text;
    pure tool_use or thinking entries are skipped.
    """
    if not transcript_path:
        return ""
    try:
        with open(transcript_path, "r", encoding="utf-8") as fh:
            lines = fh.readlines()
    except OSError:
        return ""
    for raw in reversed(lines):
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


def _split_sentences(text: str):
    # Split on sentence terminators and newlines; keep it simple.
    return re.split(r"[.!?\n]+", text)


def has_combo_violation(text: str) -> bool:
    for sentence in _split_sentences(text):
        words = {w.lower() for w in re.findall(r"\b[\w']+\b", sentence)}
        hits = COMBO_TOKENS & words
        if not hits:
            continue
        non_this = hits - {"this"}
        # >=2 distinct combo tokens (any pair, including non-"this" pairs).
        if len(hits) >= 2 and non_this:
            return True
        # "this" alone in the sentence — pair with deflection partners.
        if "this" in hits and (THIS_PARTNERS & words):
            partners = (THIS_PARTNERS & words) - {"this"}
            if partners:
                return True
    return False


def main() -> None:
    try:
        payload = json.load(sys.stdin)
    except ValueError:
        sys.exit(0)

    text = last_assistant_text(payload.get("transcript_path", ""))
    if not text:
        sys.exit(0)

    triggered = bool(PHRASE_PATTERN.search(text)) or has_combo_violation(text)
    if triggered:
        json.dump(
            {"decision": "block", "reason": REPLAN, "systemMessage": REPLAN},
            sys.stdout,
        )
    sys.exit(0)


if __name__ == "__main__":
    main()
