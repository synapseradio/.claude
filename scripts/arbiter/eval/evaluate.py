#!/usr/bin/env python3
"""Evaluate an arbiter configuration against the labeled corpus.

Runs every ``(record, verdict)`` pair through the configured judge
server, compares each output to the ground-truth label, and produces a
per-verdict confusion matrix plus latency p50/p95 and peak RSS while
the run was in flight. Outputs both a JSON report (machine-readable)
and a markdown report (human-readable).

Same labeled corpus, multiple configs: diff the markdown reports to
see which knob actually moved the needle.

Usage:

    python3 evaluate.py --config configs/baseline.yaml
    python3 evaluate.py --config configs/baseline.yaml \\
        --corpus corpus.labeled.jsonl \\
        --output reports/baseline-2026-05-15.json

A health probe runs first; if the daemon is unreachable, the harness
exits non-zero before touching the corpus.
"""

from __future__ import annotations

import argparse
import contextlib
import json
import os
import re
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

import yaml

# Reuse production bindings loader for validated verdict prompts.
_ARBITER_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ARBITER_ROOT))
from lib.config import load_bindings  # noqa: E402
from lib.frame import get_framing  # noqa: E402

VERDICTS = (
    "open_questions",
    "uncommitted_alternatives",
    "out_of_scope_deferral",
    "baseline_probe",
)

_OUTPUT_INSTRUCTIONS = {
    "json_schema": ('\n\nOutput exactly `{"yes": true}` or `{"yes": false}`. JSON only, no prose.'),
    "choice_grammar": "\n\nOutput exactly `yes` or `no`. One word, lowercase.",
    "free_form": ("\n\nAnswer with exactly one word: `yes` or `no`. Nothing else, no punctuation."),
}

_YES_NO_SCHEMA = {
    "type": "object",
    "properties": {"yes": {"type": "boolean"}},
    "required": ["yes"],
}

# Qwen3 emits `<think>...</think>` reasoning blocks by default. The
# `/no_think` directive in the system prompt collapses the block to an
# empty pair of tags but does not remove them. Strip the tag span before
# parsing so the free_form parser sees only the answer.
_THINK_BLOCK = re.compile(r"<think>.*?</think>\s*", re.DOTALL)


# ── client ────────────────────────────────────────────────────────────


class JudgeError(Exception):
    pass


class JudgeClient:
    """HTTP client to an OpenAI-compatible chat-completions server.

    Mirrors ``lib.client._post_chat`` so baseline numbers match
    production behavior. Output mode is selected from the config so
    Phase 1 can plug in a choice-grammar variant without touching the
    harness.
    """

    def __init__(self, server_cfg: dict, output_cfg: dict, run_cfg: dict):
        base = server_cfg["base_url"].rstrip("/")
        self.health_url = base + server_cfg.get("health_path", "/health")
        self.chat_url = base + server_cfg.get("chat_path", "/v1/chat/completions")
        self.model = server_cfg.get("model", "judge")
        self.output_type = output_cfg.get("type", "json_schema")
        self.max_tokens = int(output_cfg.get("max_tokens", 32))
        self.cache_prompt = bool(output_cfg.get("cache_prompt", False))
        self.system_suffix = output_cfg.get("system_suffix", "") or ""
        self.timeout = float(run_cfg.get("timeout_seconds", 60))

    def probe_health(self) -> tuple[bool, str]:
        try:
            with urllib.request.urlopen(self.health_url, timeout=3) as resp:
                status = getattr(resp, "status", None) or resp.getcode()
                body = resp.read(256).decode("utf-8", errors="replace")
                if 200 <= int(status) < 300 and '"status"' in body and '"ok"' in body:
                    return True, "ok"
                return False, f"health-status:{status}"
        except urllib.error.HTTPError as exc:
            err = ""
            with contextlib.suppress(OSError):
                err = exc.read(256).decode("utf-8", errors="replace")
            if exc.code == 503 and "Loading model" in err:
                return False, "cold"
            return False, f"health-status:{exc.code}"
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            return False, f"health-error:{exc}"

    def _build_payload(self, body_text: str, framing: str, verdict_prompt: str) -> dict:
        instruction = _OUTPUT_INSTRUCTIONS.get(self.output_type)
        if instruction is None:
            raise JudgeError(f"unsupported output.type: {self.output_type!r}")
        system_prompt = framing + verdict_prompt + instruction + self.system_suffix
        framed_body = (
            "Below, between BEGIN and END markers, is the body to judge.\n\n"
            "===== BEGIN BODY =====\n"
            f"{body_text}\n"
            "===== END BODY =====\n"
        )
        payload = {
            "model": self.model,
            "stream": False,
            "max_tokens": self.max_tokens,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": framed_body},
            ],
        }
        # cache_prompt is a llama.cpp extension that controls prefix KV
        # reuse across calls. MLX-LM ignores unknown fields, so sending
        # it is harmless there. Always send the explicit value so the
        # baseline matches production exactly (which sends `false`).
        payload["cache_prompt"] = self.cache_prompt
        if self.output_type == "json_schema":
            payload["response_format"] = {
                "type": "json_schema",
                "json_schema": {"name": "yes_no", "schema": _YES_NO_SCHEMA},
            }
        elif self.output_type == "choice_grammar":
            payload["grammar"] = 'root ::= "yes" | "no"'
        # free_form: no enforcement, parser tolerates leading whitespace,
        # punctuation, and capitalization on the answer.
        return payload

    def _parse_response(self, body: dict) -> bool | None:
        choices = body.get("choices") if isinstance(body, dict) else None
        if not isinstance(choices, list) or not choices:
            return None
        message = choices[0].get("message") if isinstance(choices[0], dict) else None
        content = message.get("content") if isinstance(message, dict) else None
        if not isinstance(content, str) or not content.strip():
            return None
        if self.output_type == "json_schema":
            try:
                parsed = json.loads(content)
            except ValueError:
                return None
            v = parsed.get("yes") if isinstance(parsed, dict) else None
            return v if isinstance(v, bool) else None
        if self.output_type == "choice_grammar":
            tok = content.strip().lower()
            if tok == "yes":
                return True
            if tok == "no":
                return False
            return None
        if self.output_type == "free_form":
            cleaned = _THINK_BLOCK.sub("", content)
            tok = cleaned.strip().lower().lstrip("`'\"")
            words = tok.split() if tok else []
            if not words:
                return None
            head = words[0].rstrip("`.,!?;:'\"")
            if head.startswith("yes"):
                return True
            if head.startswith("no"):
                return False
            return None
        return None

    def judge(self, body_text: str, framing: str, verdict_prompt: str) -> tuple[bool | None, float]:
        payload = json.dumps(self._build_payload(body_text, framing, verdict_prompt)).encode()
        request = urllib.request.Request(
            self.chat_url,
            data=payload,
            method="POST",
            headers={"content-type": "application/json"},
        )
        started = time.monotonic()
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as resp:
                body = json.load(resp)
            elapsed = time.monotonic() - started
            return self._parse_response(body), elapsed
        except urllib.error.HTTPError, urllib.error.URLError, TimeoutError, OSError, ValueError:
            elapsed = time.monotonic() - started
            return None, elapsed

    def warmup(self) -> None:
        # One throwaway call to absorb cold weight load.
        self.judge("warmup", "warmup framing.\n\n", "warmup prompt")


# ── memory sampler ────────────────────────────────────────────────────


class MemorySampler:
    """Polls ``ps -o rss=`` on the judge PID at a fixed interval and
    captures ``vmmap --summary`` once at stop. Peak RSS is the maximum
    sample observed during the run.
    """

    def __init__(self, pid_file: Path | None, interval: float = 0.5):
        self.pid_file = pid_file
        self.interval = interval
        self.samples: list[int] = []
        self.pid: int | None = None
        self.vmmap_summary: str | None = None
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def _read_pid(self) -> int | None:
        if self.pid_file is None:
            return None
        try:
            return int(self.pid_file.read_text().strip())
        except OSError, ValueError:
            return None

    def _loop(self) -> None:
        pid = self._read_pid()
        if pid is None:
            return
        self.pid = pid
        while not self._stop.is_set():
            try:
                out = subprocess.check_output(
                    ["ps", "-o", "rss=", "-p", str(pid)],
                    text=True,
                    stderr=subprocess.DEVNULL,
                )
                self.samples.append(int(out.strip()))
            except subprocess.CalledProcessError, ValueError:
                pass
            self._stop.wait(self.interval)

    def start(self) -> None:
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=2)
        if self.pid is not None:
            with contextlib.suppress(
                subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired
            ):
                self.vmmap_summary = subprocess.check_output(
                    ["vmmap", "--summary", str(self.pid)],
                    text=True,
                    stderr=subprocess.DEVNULL,
                    timeout=10,
                )

    def peak_rss_kb(self) -> int | None:
        return max(self.samples) if self.samples else None


# ── metrics ───────────────────────────────────────────────────────────


@dataclass
class Calls:
    label_true_pred_true: int = 0  # TP
    label_false_pred_true: int = 0  # FP
    label_false_pred_false: int = 0  # TN
    label_true_pred_false: int = 0  # FN
    errors: int = 0
    latencies_ms: list[float] = field(default_factory=list)


def _record_call(calls: Calls, label: bool, pred: bool | None, latency_ms: float) -> None:
    calls.latencies_ms.append(latency_ms)
    if pred is None:
        calls.errors += 1
        return
    if label and pred:
        calls.label_true_pred_true += 1
    elif label and not pred:
        calls.label_true_pred_false += 1
    elif (not label) and pred:
        calls.label_false_pred_true += 1
    else:
        calls.label_false_pred_false += 1


def _safe_div(num: float, den: float) -> float:
    return num / den if den else 0.0


def _latency_stats(values: list[float]) -> dict:
    if not values:
        return {"count": 0, "p50": None, "p95": None, "p99": None, "max": None, "mean": None}
    s = sorted(values)
    n = len(s)

    def pct(p: float) -> float:
        idx = min(n - 1, int(n * p))
        return s[idx]

    return {
        "count": n,
        "p50": round(pct(0.50), 1),
        "p95": round(pct(0.95), 1),
        "p99": round(pct(0.99), 1),
        "max": round(s[-1], 1),
        "mean": round(sum(s) / n, 1),
    }


def _verdict_metrics(calls: Calls) -> dict:
    tp = calls.label_true_pred_true
    fp = calls.label_false_pred_true
    tn = calls.label_false_pred_false
    fn = calls.label_true_pred_false
    total = tp + fp + tn + fn
    precision = _safe_div(tp, tp + fp)
    recall = _safe_div(tp, tp + fn)
    f1 = _safe_div(2 * precision * recall, precision + recall)
    accuracy = _safe_div(tp + tn, total)
    return {
        "tp": tp,
        "fp": fp,
        "tn": tn,
        "fn": fn,
        "errors": calls.errors,
        "total_labeled": total,
        "precision": round(precision, 3),
        "recall": round(recall, 3),
        "f1": round(f1, 3),
        "accuracy": round(accuracy, 3),
        "latency_ms": _latency_stats(calls.latencies_ms),
    }


# ── corpus ────────────────────────────────────────────────────────────


def load_corpus(path: Path) -> list[dict]:
    out: list[dict] = []
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except ValueError:
                continue
            if rec.get("labels") and isinstance(rec["labels"], dict):
                out.append(rec)
    return out


# ── framings ──────────────────────────────────────────────────────────


def framing_for(event: str) -> str | None:
    """Map a corpus event token to the framing arbiter uses in production.

    Corpus events are ``Stop`` or ``PreToolUse:ExitPlanMode``. The
    production framing map keys on the hook event alone — Stop /
    SubagentStop / PreToolUse — so the corpus token is split before
    lookup.
    """
    hook_event = event.split(":", 1)[0]
    return get_framing(hook_event)


# ── runner ────────────────────────────────────────────────────────────


def run(config: dict, corpus: list[dict], sample_memory: bool) -> dict:
    config_dir = Path(config["__config_dir__"])
    bindings_path = (config_dir / config["prompts"]["bindings"]).resolve()
    bindings = load_bindings(bindings_path)

    verdict_specs = {v: bindings.verdicts[v] for v in VERDICTS if v in bindings.verdicts}
    missing = [v for v in VERDICTS if v not in bindings.verdicts]
    if missing:
        sys.stderr.write(f"warning: bindings.yaml missing verdicts {missing}\n")

    client = JudgeClient(config["server"], config["output"], config.get("run", {}))

    healthy, reason = client.probe_health()
    if not healthy:
        raise JudgeError(f"judge not healthy: {reason}")

    if config.get("run", {}).get("warmup", True):
        client.warmup()

    pid_file = None
    pf = config["server"].get("pid_file")
    if pf:
        pid_file = Path(os.path.expanduser(pf))

    sampler = MemorySampler(pid_file) if sample_memory else None
    if sampler is not None:
        sampler.start()

    per_verdict: dict[str, Calls] = {v: Calls() for v in verdict_specs}
    started = time.monotonic()
    for idx, rec in enumerate(corpus, start=1):
        framing = framing_for(rec["event"])
        if framing is None:
            continue
        body = rec["body_stripped"]
        labels = rec["labels"]
        for vid, spec in verdict_specs.items():
            if vid not in labels:
                continue
            pred, latency = client.judge(body, framing, spec.prompt)
            _record_call(per_verdict[vid], bool(labels[vid]), pred, latency * 1000)
        if idx % 25 == 0:
            sys.stderr.write(f"  evaluated {idx}/{len(corpus)} records\n")
    wall_seconds = time.monotonic() - started

    if sampler is not None:
        sampler.stop()

    overall_latencies = [lat for calls in per_verdict.values() for lat in calls.latencies_ms]
    overall_errors = sum(calls.errors for calls in per_verdict.values())

    return {
        "config_name": config.get("name", "<unnamed>"),
        "config_description": config.get("description", ""),
        "timestamp_utc": datetime.now(UTC).isoformat(timespec="seconds"),
        "corpus_path": config.get("__corpus_path__"),
        "corpus_size": len(corpus),
        "bindings_path": str(bindings_path),
        "per_verdict": {vid: _verdict_metrics(calls) for vid, calls in per_verdict.items()},
        "overall": {
            "calls": len(overall_latencies),
            "errors": overall_errors,
            "wall_seconds": round(wall_seconds, 2),
            "latency_ms": _latency_stats(overall_latencies),
        },
        "memory": {
            "peak_rss_kb": sampler.peak_rss_kb() if sampler else None,
            "samples": len(sampler.samples) if sampler else 0,
            "vmmap_summary": sampler.vmmap_summary if sampler else None,
            "pid": sampler.pid if sampler else None,
        },
    }


# ── reporting ─────────────────────────────────────────────────────────


def _fmt_ms(stats: dict) -> str:
    if not stats or stats.get("count", 0) == 0:
        return "—"
    return f"p50 {stats['p50']:.0f} / p95 {stats['p95']:.0f} / max {stats['max']:.0f}"


def render_markdown(report: dict) -> str:
    lines: list[str] = []
    lines.append(f"# Eval report: {report['config_name']}")
    lines.append("")
    lines.append(f"- Run UTC: {report['timestamp_utc']}")
    lines.append(f"- Corpus: {report.get('corpus_path')} ({report['corpus_size']} labeled records)")
    lines.append(f"- Bindings: {report['bindings_path']}")
    lines.append("")
    if report["config_description"]:
        lines.append("> " + report["config_description"].replace("\n", "\n> "))
        lines.append("")

    lines.append("## Per-verdict quality")
    lines.append("")
    lines.append(
        "| Verdict | TP | FP | TN | FN | Err | Precision | Recall | F1 | Accuracy | Latency (ms) |"
    )
    lines.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|")
    for vid, m in report["per_verdict"].items():
        lines.append(
            f"| {vid} | {m['tp']} | {m['fp']} | {m['tn']} | {m['fn']} | {m['errors']} "
            f"| {m['precision']:.3f} | {m['recall']:.3f} | {m['f1']:.3f} "
            f"| {m['accuracy']:.3f} | {_fmt_ms(m['latency_ms'])} |"
        )
    lines.append("")

    overall = report["overall"]
    lines.append("## Overall")
    lines.append("")
    lines.append(f"- Calls: {overall['calls']}")
    lines.append(f"- Errors: {overall['errors']}")
    lines.append(f"- Wall: {overall['wall_seconds']:.1f}s")
    lines.append(f"- Latency: {_fmt_ms(overall['latency_ms'])}")
    lines.append("")

    mem = report["memory"]
    lines.append("## Memory")
    lines.append("")
    if mem["peak_rss_kb"] is not None:
        lines.append(
            f"- Peak RSS: {mem['peak_rss_kb'] / 1024:.0f} MiB "
            f"({mem['samples']} samples, pid {mem['pid']})"
        )
    else:
        lines.append("- Peak RSS: not measured")
    if mem.get("vmmap_summary"):
        lines.append("")
        lines.append("<details><summary>vmmap --summary</summary>")
        lines.append("")
        lines.append("```")
        lines.append(mem["vmmap_summary"].rstrip())
        lines.append("```")
        lines.append("")
        lines.append("</details>")
    lines.append("")
    return "\n".join(lines)


# ── cli ───────────────────────────────────────────────────────────────


def main() -> int:
    here = Path(__file__).resolve().parent
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("--config", type=Path, default=here / "configs" / "baseline.yaml")
    ap.add_argument("--corpus", type=Path, default=here / "corpus.labeled.jsonl")
    ap.add_argument(
        "--output",
        type=Path,
        default=None,
        help="JSON report path. Defaults to reports/<config-name>-<ts>.json.",
    )
    ap.add_argument(
        "--no-memory",
        action="store_true",
        help="Skip the RSS poll and vmmap snapshot (useful when no PID is reachable).",
    )
    args = ap.parse_args()

    if not args.config.exists():
        sys.stderr.write(f"missing config: {args.config}\n")
        return 1
    if not args.corpus.exists():
        sys.stderr.write(f"missing corpus: {args.corpus}\n")
        sys.stderr.write("run label.py first to produce a labeled corpus.\n")
        return 1

    with args.config.open(encoding="utf-8") as fh:
        config = yaml.safe_load(fh)
    config["__config_dir__"] = str(args.config.resolve().parent)
    config["__corpus_path__"] = str(args.corpus.resolve())

    corpus = load_corpus(args.corpus)
    if not corpus:
        sys.stderr.write(f"corpus has no labeled records: {args.corpus}\n")
        return 1

    sys.stderr.write(
        f"config: {config.get('name')}\ncorpus: {args.corpus} ({len(corpus)} labeled records)\n"
    )

    report = run(config, corpus, sample_memory=not args.no_memory)

    if args.output is None:
        ts = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        args.output = here / "reports" / f"{report['config_name']}-{ts}.json"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2, ensure_ascii=False)

    md_path = args.output.with_suffix(".md")
    md_path.write_text(render_markdown(report), encoding="utf-8")

    sys.stderr.write(f"wrote {args.output}\n")
    sys.stderr.write(f"wrote {md_path}\n")
    # Print the markdown summary to stdout for easy capture.
    sys.stdout.write(render_markdown(report))
    return 0


if __name__ == "__main__":
    sys.exit(main())
