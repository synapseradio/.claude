#!/usr/bin/env python3
"""Capture an arbiter evaluation corpus from existing transcripts.

Walks transcript files under one or more roots (default
``~/.claude/projects``) and produces a JSONL corpus of arbiter-eligible
events. Every text-bearing assistant entry becomes a synthetic Stop
event record; every ``ExitPlanMode`` tool_use becomes a
``PreToolUse:ExitPlanMode`` record. Each record carries the body
extracted the same way arbiter extracts it in production — code-
stripping is reused from ``lib.extract`` directly so the corpus body
matches what the judge actually sees.

When ``--arbiter-log`` is provided, each event is correlated by
timestamp to the production arbiter.log within a small window. The raw
``verdicts=`` string from the matched log line is recorded as
``arbiter_log_match`` for the labeling tool to interpret. Provisional
matches are signal, not ground truth — the labeler decides.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

# Reuse the production code-stripping so the corpus body matches the
# string the judge actually receives. Any divergence between this tool
# and lib/extract.py would silently change what the corpus represents.
_ARBITER_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ARBITER_ROOT))
from lib.extract import strip_code  # noqa: E402

# arbiter.log format:
#   "2026-05-09T13:24:28Z  event=Stop  duration_ms=1799  verdicts=OUT_OF_SCOPE_DEFERRAL"
_LOG_LINE = re.compile(
    r"^(?P<ts>\S+)\s+event=(?P<event>\S+)\s+"
    r"duration_ms=(?P<dur>\d+)\s+verdicts=(?P<verdicts>\S+)$"
)

# Map corpus event names to the event= values arbiter writes to the log.
_LOG_EVENT_FOR = {
    "Stop": "Stop",
    "PreToolUse:ExitPlanMode": "PreToolUse",
    "SubagentStop": "SubagentStop",
}


def stable_id(event: str, body_stripped: str) -> str:
    digest = hashlib.sha256(f"{event}\0{body_stripped}".encode()).hexdigest()
    return digest[:16]


def parse_transcript_lines(path: Path):
    try:
        fh = path.open(encoding="utf-8")
    except OSError:
        return
    with fh:
        for line_no, raw in enumerate(fh, start=1):
            stripped = raw.strip()
            if not stripped:
                continue
            try:
                yield line_no, json.loads(stripped)
            except ValueError:
                continue


def assistant_text(entry: dict) -> str:
    """Text of a single assistant entry. Joins multiple text blocks
    inside one entry the same way ``lib.extract.last_assistant_text``
    does. Returns "" when the entry has no text content."""
    if entry.get("type") != "assistant":
        return ""
    content = entry.get("message", {}).get("content", [])
    if isinstance(content, str):
        return content if content.strip() else ""
    if isinstance(content, list):
        parts = [
            block.get("text", "")
            for block in content
            if isinstance(block, dict) and block.get("type") == "text"
        ]
        joined = "\n".join(parts)
        return joined if joined.strip() else ""
    return ""


def plan_bodies(entry: dict):
    """Yield plan-body strings from ``ExitPlanMode`` tool_use blocks in
    a single assistant entry. Selection of which key inside ``input``
    holds the plan mirrors ``lib.extract._plan_extractor``."""
    if entry.get("type") != "assistant":
        return
    content = entry.get("message", {}).get("content", [])
    if not isinstance(content, list):
        return
    for block in content:
        if not isinstance(block, dict):
            continue
        if block.get("type") != "tool_use" or block.get("name") != "ExitPlanMode":
            continue
        ti = block.get("input") or {}
        if not isinstance(ti, dict):
            continue
        picked: str | None = None
        for key in ("plan", "content", "summary", "text", "body"):
            v = ti.get(key)
            if isinstance(v, str) and v.strip():
                picked = v
                break
        if picked is None:
            extras = [v for v in ti.values() if isinstance(v, str) and v.strip()]
            if extras:
                picked = "\n".join(extras)
        if picked is not None:
            yield picked


def entry_timestamp(entry: dict) -> datetime | None:
    ts = entry.get("timestamp")
    if not isinstance(ts, str):
        return None
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except ValueError:
        return None


@dataclass
class LogEntry:
    ts: datetime
    event: str
    verdicts_raw: str


def parse_arbiter_log(path: Path) -> list[LogEntry]:
    if not path.exists():
        return []
    out: list[LogEntry] = []
    with path.open(encoding="utf-8") as fh:
        for raw in fh:
            m = _LOG_LINE.match(raw.strip())
            if not m:
                continue
            try:
                ts = datetime.fromisoformat(m["ts"].replace("Z", "+00:00"))
            except ValueError:
                continue
            out.append(LogEntry(ts=ts, event=m["event"], verdicts_raw=m["verdicts"]))
    return out


def correlate(
    ts: datetime | None,
    corpus_event: str,
    log: list[LogEntry],
    window: timedelta = timedelta(seconds=10),
) -> str | None:
    if ts is None or not log:
        return None
    target = _LOG_EVENT_FOR.get(corpus_event)
    if target is None:
        return None
    best: LogEntry | None = None
    best_dt = window
    for entry in log:
        if entry.event != target:
            continue
        dt = abs(entry.ts - ts)
        if dt <= best_dt:
            best_dt = dt
            best = entry
    return best.verdicts_raw if best is not None else None


def iter_transcripts(roots):
    for root in roots:
        if not root.exists():
            continue
        yield from root.rglob("*.jsonl")


def emit(
    out_fh,
    *,
    rid: str,
    event: str,
    transcript: Path,
    line_no: int,
    ts: datetime | None,
    body: str,
    body_stripped: str,
    arbiter_log_match: str | None,
) -> None:
    record = {
        "id": rid,
        "event": event,
        "source": {
            "transcript": str(transcript),
            "line_no": line_no,
            "timestamp": ts.isoformat() if ts else None,
        },
        "body": body,
        "body_stripped": body_stripped,
        "arbiter_log_match": arbiter_log_match,
        "labels": None,
    }
    out_fh.write(json.dumps(record, ensure_ascii=False) + "\n")


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument(
        "--transcript-root",
        action="append",
        type=Path,
        metavar="DIR",
        help="Root to scan for *.jsonl transcripts. Repeatable. Defaults to ~/.claude/projects.",
    )
    ap.add_argument(
        "--arbiter-log",
        type=Path,
        default=Path.home() / ".claude" / "arbiter" / "logs" / "arbiter.log",
        help="arbiter.log to correlate events to for provisional labels.",
    )
    ap.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).resolve().parent / "corpus.unlabeled.jsonl",
    )
    ap.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Max records to emit. 0 means unlimited.",
    )
    ap.add_argument(
        "--min-body-chars",
        type=int,
        default=40,
        help="Skip bodies shorter than this many chars after code stripping.",
    )
    args = ap.parse_args()

    roots = args.transcript_root or [Path.home() / ".claude" / "projects"]
    log_entries = parse_arbiter_log(args.arbiter_log)

    seen: set[str] = set()
    written = 0
    args.output.parent.mkdir(parents=True, exist_ok=True)

    with args.output.open("w", encoding="utf-8") as out_fh:
        for transcript in iter_transcripts(roots):
            for line_no, entry in parse_transcript_lines(transcript):
                ts = entry_timestamp(entry)

                text = assistant_text(entry)
                if text:
                    stripped = strip_code(text)
                    if len(stripped.strip()) >= args.min_body_chars:
                        rid = stable_id("Stop", stripped)
                        if rid not in seen:
                            seen.add(rid)
                            emit(
                                out_fh,
                                rid=rid,
                                event="Stop",
                                transcript=transcript,
                                line_no=line_no,
                                ts=ts,
                                body=text,
                                body_stripped=stripped,
                                arbiter_log_match=correlate(ts, "Stop", log_entries),
                            )
                            written += 1
                            if args.limit and written >= args.limit:
                                sys.stderr.write(f"wrote {written} records to {args.output}\n")
                                return 0

                for plan in plan_bodies(entry):
                    stripped = strip_code(plan)
                    if len(stripped.strip()) < args.min_body_chars:
                        continue
                    rid = stable_id("PreToolUse:ExitPlanMode", stripped)
                    if rid in seen:
                        continue
                    seen.add(rid)
                    emit(
                        out_fh,
                        rid=rid,
                        event="PreToolUse:ExitPlanMode",
                        transcript=transcript,
                        line_no=line_no,
                        ts=ts,
                        body=plan,
                        body_stripped=stripped,
                        arbiter_log_match=correlate(ts, "PreToolUse:ExitPlanMode", log_entries),
                    )
                    written += 1
                    if args.limit and written >= args.limit:
                        sys.stderr.write(f"wrote {written} records to {args.output}\n")
                        return 0

    sys.stderr.write(f"wrote {written} records to {args.output}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
