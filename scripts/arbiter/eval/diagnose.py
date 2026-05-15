#!/usr/bin/env python3
"""Print the bodies that a candidate config got wrong, grouped by FP/FN.

Re-runs the configured judge against the labeled corpus (same as
evaluate.py) but instead of summarizing, dumps every disagreement as
JSON with the body excerpt. Lets you read what the small model is
actually confused by, so the bindings prompt can be sharpened against
those specific patterns.

Usage:

    python3 diagnose.py --config configs/mlx-qwen3-1.7b.yaml \\
        --verdict baseline_probe --limit 20

If ``--verdict`` is omitted, prints disagreements for every verdict.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))
from evaluate import VERDICTS, JudgeClient, framing_for, load_corpus  # noqa: E402

_ARBITER_ROOT = _HERE.parent
sys.path.insert(0, str(_ARBITER_ROOT))
from lib.config import load_bindings  # noqa: E402


def _excerpt(text: str, max_chars: int = 400) -> str:
    text = text.strip()
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + f"… (+{len(text) - max_chars} chars)"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--config", type=Path, required=True)
    ap.add_argument("--corpus", type=Path, default=_HERE / "corpus.labeled.jsonl")
    ap.add_argument("--verdict", choices=VERDICTS, default=None)
    ap.add_argument(
        "--limit", type=int, default=10, help="Max FP+FN examples to print per verdict."
    )
    ap.add_argument(
        "--full-body",
        action="store_true",
        help="Print the entire body. Default is 400-char excerpt.",
    )
    args = ap.parse_args()

    with args.config.open(encoding="utf-8") as fh:
        cfg = yaml.safe_load(fh)
    bindings_path = (args.config.resolve().parent / cfg["prompts"]["bindings"]).resolve()
    bindings = load_bindings(bindings_path)
    client = JudgeClient(cfg["server"], cfg["output"], cfg.get("run", {}))
    healthy, reason = client.probe_health()
    if not healthy:
        sys.stderr.write(f"judge not healthy: {reason}\n")
        return 1
    if cfg.get("run", {}).get("warmup", True):
        client.warmup()

    corpus = load_corpus(args.corpus)
    target_verdicts = [args.verdict] if args.verdict else list(VERDICTS)

    for vid in target_verdicts:
        if vid not in bindings.verdicts:
            continue
        spec = bindings.verdicts[vid]
        fps: list[dict] = []
        fns: list[dict] = []
        for rec in corpus:
            framing = framing_for(rec["event"])
            if framing is None:
                continue
            if vid not in rec["labels"]:
                continue
            label = bool(rec["labels"][vid])
            pred, _ = client.judge(rec["body_stripped"], framing, spec.prompt)
            if pred is None or pred == label:
                continue
            entry = {
                "id": rec["id"],
                "event": rec["event"],
                "label": label,
                "pred": pred,
                "body": rec["body_stripped"] if args.full_body else _excerpt(rec["body_stripped"]),
            }
            if pred and not label:
                fps.append(entry)
            elif label and not pred:
                fns.append(entry)
            if len(fps) + len(fns) >= args.limit:
                break

        print(f"\n=== {vid} ===")
        print(f"false positives (predicted yes, label was no): {len(fps)}")
        for e in fps:
            print(json.dumps(e, ensure_ascii=False))
        print(f"false negatives (predicted no, label was yes): {len(fns)}")
        for e in fns:
            print(json.dumps(e, ensure_ascii=False))

    return 0


if __name__ == "__main__":
    sys.exit(main())
