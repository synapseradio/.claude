#!/usr/bin/env python3
"""Diff two evaluation reports produced by ``evaluate.py``.

Compares per-verdict precision/recall/F1, latency percentiles, error
counts, and peak RSS. Output is a markdown table showing the delta
between baseline and candidate. Anything outside the quality bar in
``quality-bar.yaml`` is flagged.

Usage:

    python3 compare.py BASELINE.json CANDIDATE.json
    python3 compare.py BASELINE.json CANDIDATE.json --bar quality-bar.yaml
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml

_HERE = Path(__file__).resolve().parent


def _fmt_delta(a: float | None, b: float | None, digits: int = 3) -> str:
    if a is None or b is None:
        return "—"
    if a == b:
        return f"{b:.{digits}f}  (=)"
    delta = b - a
    sign = "+" if delta > 0 else ""
    return f"{b:.{digits}f}  ({sign}{delta:.{digits}f})"


def _fmt_ms_delta(a: dict, b: dict, key: str) -> str:
    av = a.get(key) if a else None
    bv = b.get(key) if b else None
    if av is None and bv is None:
        return "—"
    if av is None:
        return f"{bv:.0f}"
    if bv is None:
        return f"({av:.0f}) → —"
    delta = bv - av
    sign = "+" if delta > 0 else ""
    return f"{bv:.0f} ({sign}{delta:.0f})"


def _check_bar(per_verdict: dict, bar: dict) -> list[str]:
    misses: list[str] = []
    for vid, thresholds in (bar or {}).get("per_verdict", {}).items():
        m = per_verdict.get(vid)
        if m is None:
            continue
        if m["precision"] < thresholds.get("min_precision", 0):
            misses.append(f"{vid}: precision {m['precision']:.3f} < {thresholds['min_precision']}")
        if m["recall"] < thresholds.get("min_recall", 0):
            misses.append(f"{vid}: recall {m['recall']:.3f} < {thresholds['min_recall']}")
        if m["f1"] < thresholds.get("min_f1", 0):
            misses.append(f"{vid}: f1 {m['f1']:.3f} < {thresholds['min_f1']}")
    return misses


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("baseline", type=Path)
    ap.add_argument("candidate", type=Path)
    ap.add_argument(
        "--bar",
        type=Path,
        default=_HERE / "quality-bar.yaml",
        help="Quality bar YAML. Misses are flagged in the output.",
    )
    args = ap.parse_args()

    if not args.baseline.exists():
        sys.stderr.write(f"missing baseline report: {args.baseline}\n")
        return 1
    if not args.candidate.exists():
        sys.stderr.write(f"missing candidate report: {args.candidate}\n")
        return 1

    base = json.loads(args.baseline.read_text(encoding="utf-8"))
    cand = json.loads(args.candidate.read_text(encoding="utf-8"))
    bar: dict = {}
    if args.bar and args.bar.exists():
        bar = yaml.safe_load(args.bar.read_text(encoding="utf-8")) or {}

    print(f"# {base['config_name']}  →  {cand['config_name']}")
    print()
    print(
        f"Corpus: {base.get('corpus_size')} records (baseline) "
        f"vs {cand.get('corpus_size')} (candidate)"
    )
    print()

    print("## Per-verdict deltas")
    print()
    print("| Verdict | Precision | Recall | F1 | Accuracy | p95 latency (ms) | Errors |")
    print("|---|---|---|---|---|---|---|")
    for vid in base["per_verdict"]:
        if vid not in cand["per_verdict"]:
            continue
        b = base["per_verdict"][vid]
        c = cand["per_verdict"][vid]
        print(
            f"| {vid} "
            f"| {_fmt_delta(b['precision'], c['precision'])} "
            f"| {_fmt_delta(b['recall'], c['recall'])} "
            f"| {_fmt_delta(b['f1'], c['f1'])} "
            f"| {_fmt_delta(b['accuracy'], c['accuracy'])} "
            f"| {_fmt_ms_delta(b['latency_ms'], c['latency_ms'], 'p95')} "
            f"| {c['errors']} (was {b['errors']}) |"
        )
    print()

    print("## System deltas")
    print()
    base_rss = base["memory"].get("peak_rss_kb")
    cand_rss = cand["memory"].get("peak_rss_kb")
    if base_rss is not None and cand_rss is not None:
        delta_mib = (cand_rss - base_rss) / 1024
        sign = "+" if delta_mib > 0 else ""
        pct = 100 * (cand_rss - base_rss) / base_rss
        print(
            f"- Peak RSS: {base_rss / 1024:.0f} MiB  →  {cand_rss / 1024:.0f} MiB  "
            f"({sign}{delta_mib:.0f} MiB, {pct:+.1f}%)"
        )
    elif cand_rss is not None:
        print(f"- Peak RSS: candidate {cand_rss / 1024:.0f} MiB (no baseline)")
    base_lat = base["overall"]["latency_ms"]
    cand_lat = cand["overall"]["latency_ms"]
    print(f"- Latency p50: {_fmt_ms_delta(base_lat, cand_lat, 'p50')}")
    print(f"- Latency p95: {_fmt_ms_delta(base_lat, cand_lat, 'p95')}")
    print(
        f"- Wall: {base['overall']['wall_seconds']:.1f}s  →  {cand['overall']['wall_seconds']:.1f}s"
    )
    print()

    if bar:
        misses = _check_bar(cand["per_verdict"], bar)
        sys_bar = bar.get("system", {})
        if (
            cand_lat.get("p95")
            and sys_bar.get("max_latency_p95_ms")
            and cand_lat["p95"] > sys_bar["max_latency_p95_ms"]
        ):
            misses.append(
                f"system: p95 latency {cand_lat['p95']:.0f}ms > {sys_bar['max_latency_p95_ms']}ms"
            )
        if cand_rss and sys_bar.get("max_peak_rss_mib"):
            cand_mib = cand_rss / 1024
            if cand_mib > sys_bar["max_peak_rss_mib"]:
                misses.append(
                    f"system: peak RSS {cand_mib:.0f}MiB > {sys_bar['max_peak_rss_mib']}MiB"
                )
        if cand["overall"]["errors"] > sys_bar.get("max_errors_per_run", 0):
            misses.append(
                f"system: errors {cand['overall']['errors']} > "
                f"{sys_bar.get('max_errors_per_run', 0)}"
            )

        print("## Quality bar")
        print()
        if misses:
            print(f"❌ Candidate misses {len(misses)} threshold(s):")
            print()
            for m in misses:
                print(f"- {m}")
        else:
            print("✅ Candidate clears all quality-bar thresholds.")
        print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
