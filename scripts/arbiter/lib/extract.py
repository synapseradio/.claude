"""Body extractors per `(event, tool)` and turn-tool collection.

Built-in map keyed on `(event, tool)`. Ships an extractor for every
target referenced by `bindings.yaml`. A pair with no matching
extractor returns `None`, and the dispatcher treats that as a no-op
rather than guessing wrong.

Code stripping leaves the model judging the assistant's own prose,
not strings or commands the assistant happened to echo back.
"""

import json
import re

CODE_FENCE = re.compile(r"```[\s\S]*?```|~~~[\s\S]*?~~~")
INLINE_CODE = re.compile(r"`[^`\n]*`")


def strip_code(text: str) -> str:
    text = CODE_FENCE.sub("", text)
    text = INLINE_CODE.sub("", text)
    return text


def _read_transcript_lines(transcript_path: str) -> list[str]:
    if not transcript_path:
        return []
    try:
        with open(transcript_path, encoding="utf-8") as fh:
            return fh.readlines()
    except OSError:
        return []


def last_assistant_text(transcript_path: str) -> str:
    """Most recent text-bearing assistant entry's text.

    A single assistant turn may produce multiple transcript entries
    (thinking / tool_use / text). The most recent text-bearing entry
    is the body Arbiter judges. Pure `tool_use` or `thinking` entries
    are skipped.
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
    """Tool_use names from the latest turn — assistant entries since the
    last user entry.

    Walks the transcript from the end, stops at the first user entry
    (which marks the boundary of the current turn), and collects every
    `tool_use` block name found among assistant entries in between.
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


def _plan_extractor(payload: dict) -> str:
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


def _stop_extractor(payload: dict) -> str:
    transcript_path = payload.get("transcript_path", "") or ""
    return last_assistant_text(transcript_path)


_EXTRACTORS = {
    ("PreToolUse", "ExitPlanMode"): _plan_extractor,
    ("Stop", None): _stop_extractor,
    ("SubagentStop", None): _stop_extractor,
}


def extract_body(event: str, tool: str | None, payload: dict) -> str | None:
    """Body to judge for a hook payload, or None when no extractor exists.

    The map is keyed on `(event, tool)`. A miss means Arbiter has no
    way to pull a body for that hook target — the dispatcher treats
    that as a no-op rather than guessing wrong.
    """
    fn = _EXTRACTORS.get((event, tool))
    if fn is None:
        return None
    return fn(payload)
