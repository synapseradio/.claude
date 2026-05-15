#!/usr/bin/env python3
"""Auto-label corpus records using the live judge as oracle.

Selects records the same way ``label.py`` does, but instead of
prompting the user, queries the running judge daemon for each verdict
in parallel (one slot per verdict, mirroring production fan-out) and
records the prediction as the label.

These labels are model-derived. They answer "does a candidate stack
preserve current 4B behavior?", which is what Phase 1 needs in order
to measure regression after the model/backend swap. Replace with human
labels later if absolute quality measurement is wanted; the labeling
tool ``label.py`` works on the same corpus file.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import yaml

# Reuse selection + corpus helpers from label.py and the judge client
# from evaluate.py so this tool stays in lockstep with both.
_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))
sys.path.insert(0, str(_HERE.parent))

from evaluate import JudgeClient, framing_for  # noqa: E402
from label import (  # noqa: E402
    VERDICTS,
    load_already_labeled,
    load_corpus,
    select_records,
)
from lib.config import load_bindings  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("--input", type=Path, default=_HERE / "corpus.unlabeled.jsonl")
    ap.add_argument("--output", type=Path, default=_HERE / "corpus.labeled.jsonl")
    ap.add_argument(
        "--config",
        type=Path,
        default=_HERE / "configs" / "baseline.yaml",
        help="Server config — the judge spec used as oracle.",
    )
    ap.add_argument(
        "--strategy",
        choices=(
            "mixed",
            "production-positives",
            "production-clear",
            "keyword-candidates",
            "random",
        ),
        default="mixed",
    )
    ap.add_argument("--per-category", type=int, default=20)
    ap.add_argument("--seed", type=int, default=17)
    ap.add_argument(
        "--resume",
        action="store_true",
        help="Skip records already in output. Default: overwrite output.",
    )
    args = ap.parse_args()

    if not args.input.exists():
        sys.stderr.write(f"missing input corpus: {args.input}\n")
        return 1
    if not args.config.exists():
        sys.stderr.write(f"missing config: {args.config}\n")
        return 1

    with args.config.open(encoding="utf-8") as fh:
        config = yaml.safe_load(fh)

    bindings_path = (args.config.resolve().parent / config["prompts"]["bindings"]).resolve()
    bindings = load_bindings(bindings_path)
    verdict_specs = {v: bindings.verdicts[v] for v in VERDICTS if v in bindings.verdicts}
    if len(verdict_specs) != len(VERDICTS):
        missing = [v for v in VERDICTS if v not in verdict_specs]
        sys.stderr.write(f"bindings.yaml missing verdicts: {missing}\n")
        return 1

    corpus = load_corpus(args.input)
    rng = random.Random(args.seed)
    selected = select_records(corpus, args.strategy, args.per_category, rng)

    already: dict[str, dict] = {}
    if args.resume:
        already = load_already_labeled(args.output)
        selected = [r for r in selected if r["id"] not in already]

    client = JudgeClient(config["server"], config["output"], config.get("run", {}))
    healthy, reason = client.probe_health()
    if not healthy:
        sys.stderr.write(f"judge not healthy: {reason}\n")
        return 1
    client.warmup()

    sys.stderr.write(
        f"config:   {config.get('name')}\n"
        f"corpus:   {len(corpus)} total, {len(selected)} to label\n"
        f"resume:   {args.resume} ({len(already)} already labeled)\n"
    )

    mode = "a" if args.resume else "w"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    written = 0
    errors = 0

    with args.output.open(mode, encoding="utf-8") as out_fh:
        for idx, rec in enumerate(selected, start=1):
            framing = framing_for(rec["event"])
            if framing is None:
                sys.stderr.write(
                    f"  [{idx}/{len(selected)}] skip: no framing for event={rec['event']}\n"
                )
                continue

            labels: dict[str, bool] = {}
            ok = True
            with ThreadPoolExecutor(max_workers=len(verdict_specs)) as pool:
                futures = {
                    pool.submit(client.judge, rec["body_stripped"], framing, spec.prompt): vid
                    for vid, spec in verdict_specs.items()
                }
                for fut in futures:
                    vid = futures[fut]
                    pred, _ = fut.result()
                    if pred is None:
                        ok = False
                        break
                    labels[vid] = pred

            if not ok:
                errors += 1
                sys.stderr.write(
                    f"  [{idx}/{len(selected)}] skip: judge returned None for at least one verdict\n"
                )
                continue

            rec_out = {**rec, "labels": labels, "label_source": "live-judge-4b"}
            out_fh.write(json.dumps(rec_out, ensure_ascii=False) + "\n")
            out_fh.flush()
            written += 1
            if idx % 10 == 0 or idx == len(selected):
                elapsed = time.monotonic() - started
                rate = idx / elapsed if elapsed > 0 else 0
                eta = (len(selected) - idx) / rate if rate > 0 else 0
                sys.stderr.write(
                    f"  [{idx}/{len(selected)}] {elapsed:.0f}s elapsed, "
                    f"{rate:.1f} rec/s, ETA {eta:.0f}s\n"
                )

    sys.stderr.write(f"done. {written} labeled, {errors} errors, wrote {args.output}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
