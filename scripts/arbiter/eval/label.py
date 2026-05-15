#!/usr/bin/env python3
"""Interactive labeling tool for the arbiter evaluation corpus.

Walks records from ``corpus.unlabeled.jsonl``, displays each body, and
prompts the user for a yes/no decision per verdict. Persists labels
incrementally to ``corpus.labeled.jsonl`` so a session can resume after
interruption.

Selection strategy controls which records are queued for labeling:

- ``mixed`` (default): production positives + sampled CLEAR records +
  keyword-pattern candidates per verdict. Aims to balance the corpus
  across every verdict's positive and negative classes.
- ``production-positives``: records whose ``arbiter_log_match`` names
  at least one verdict (production at 4B fired).
- ``production-clear``: records whose ``arbiter_log_match`` is
  ``CLEAR`` (production at 4B cleared the body).
- ``keyword-candidates``: records matching verdict-specific keyword
  patterns. Useful for sparse verdicts that rarely fire in production.
- ``random``: uniformly random sample.

Provisional labels are prefilled from ``arbiter_log_match``: verdicts
named in the match default to yes, verdicts not named default to no.
Press Enter at each prompt to accept the default; type ``y`` or ``n``
to override; ``s`` to skip the record; ``?`` to show the full body;
``q`` to save and quit.
"""

from __future__ import annotations

import argparse
import json
import random
import re
import sys
from pathlib import Path

VERDICTS = (
    "open_questions",
    "uncommitted_alternatives",
    "out_of_scope_deferral",
    "baseline_probe",
)

_VERDICT_NAMES = {v: v.upper() for v in VERDICTS}

# Permissive patterns that surface candidates the user can then
# label. False positives are expected — the user discriminates. The
# patterns exist so sparse verdicts get more than one or two examples
# in the labeled corpus.
_KEYWORD_PATTERNS = {
    "open_questions": re.compile(
        r"\b(?:should i|do you want|which (?:approach|one|do you)|"
        r"TBD|TODO|FIXME|not sure|unclear|up to you|your call|"
        r"prefer|either .* or)\b|\?\s*$",
        re.IGNORECASE | re.MULTILINE,
    ),
    "uncommitted_alternatives": re.compile(
        r"\b(?:two options|alternatively|or we could|either we|"
        r"option a\b|option b\b|"
        r"a\).*b\))",
        re.IGNORECASE | re.DOTALL,
    ),
    "out_of_scope_deferral": re.compile(
        r"\b(?:pre[- ]?existing|unrelated|inherited|legacy|"
        r"out[- ]of[- ]scope|leave (?:them|it|those) (?:unfixed|alone|as is))\b",
        re.IGNORECASE,
    ),
    "baseline_probe": re.compile(
        r"\b(?:check.{0,40}\b(?:main|master|trunk)\b|"
        r"stash.{0,40}\b(?:main|master|switch)\b|"
        r"on (?:main|master|trunk).{0,40}(?:fail|pass|run|exists))\b",
        re.IGNORECASE | re.DOTALL,
    ),
}


def provisional_labels(arbiter_log_match: str | None) -> dict[str, bool] | None:
    if not arbiter_log_match:
        return None
    if arbiter_log_match.startswith("ERROR"):
        return None
    if arbiter_log_match.startswith("CLEAR:quick-exit"):
        return None
    if arbiter_log_match == "CLEAR":
        return {v: False for v in VERDICTS}
    fired = set(arbiter_log_match.split(","))
    return {v: (_VERDICT_NAMES[v] in fired) for v in VERDICTS}


def load_corpus(path: Path) -> list[dict]:
    out: list[dict] = []
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except ValueError:
                continue
    return out


def load_already_labeled(path: Path) -> dict[str, dict]:
    if not path.exists():
        return {}
    out: dict[str, dict] = {}
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except ValueError:
                continue
            rid = rec.get("id")
            if isinstance(rid, str):
                out[rid] = rec
    return out


def _matches(corpus, predicate):
    return [r for r in corpus if predicate(r.get("arbiter_log_match"))]


def _is_production_positive(m: str | None) -> bool:
    return bool(m) and not m.startswith(("CLEAR", "ERROR"))


def select_records(
    corpus: list[dict], strategy: str, per_category: int, rng: random.Random
) -> list[dict]:
    if strategy == "production-positives":
        return _matches(corpus, _is_production_positive)

    if strategy == "production-clear":
        pool = _matches(corpus, lambda m: m == "CLEAR")
        rng.shuffle(pool)
        return pool[:per_category]

    if strategy == "keyword-candidates":
        seen: set[str] = set()
        out: list[dict] = []
        for verdict in VERDICTS:
            pattern = _KEYWORD_PATTERNS[verdict]
            hits = [r for r in corpus if pattern.search(r["body_stripped"])]
            rng.shuffle(hits)
            for r in hits[:per_category]:
                if r["id"] not in seen:
                    seen.add(r["id"])
                    out.append(r)
        return out

    if strategy == "random":
        pool = list(corpus)
        rng.shuffle(pool)
        return pool[:per_category]

    if strategy == "mixed":
        selected: dict[str, dict] = {}
        for r in _matches(corpus, _is_production_positive):
            selected[r["id"]] = r
        clears = _matches(corpus, lambda m: m == "CLEAR")
        rng.shuffle(clears)
        for r in clears[:per_category]:
            selected[r["id"]] = r
        for verdict in VERDICTS:
            pattern = _KEYWORD_PATTERNS[verdict]
            hits = [
                r for r in corpus if pattern.search(r["body_stripped"]) and r["id"] not in selected
            ]
            rng.shuffle(hits)
            for r in hits[:per_category]:
                selected[r["id"]] = r
        return list(selected.values())

    raise ValueError(f"unknown strategy: {strategy}")


class QuitSession(Exception):
    pass


def _show_body(body: str, max_lines: int) -> None:
    lines = body.split("\n")
    print("─" * 64)
    if len(lines) > max_lines:
        for line in lines[:max_lines]:
            print(line)
        remaining = len(lines) - max_lines
        print(f"... [{remaining} more lines; type ? at any prompt to expand]")
    else:
        for line in lines:
            print(line)
    print("─" * 64)


def prompt_label(verdict: str, default: bool, show_full) -> bool | None:
    hint = "Y/n/s/?/q" if default else "y/N/s/?/q"
    while True:
        try:
            ans = input(f"  {verdict}? [{hint}] ").strip().lower()
        except EOFError:
            raise QuitSession from None
        if ans == "":
            return default
        if ans in ("y", "yes"):
            return True
        if ans in ("n", "no"):
            return False
        if ans == "s":
            return None
        if ans == "q":
            raise QuitSession
        if ans == "?":
            show_full()
            continue
        print("    (Enter=default, y/n=label, s=skip record, ?=full body, q=save and quit)")


def label_one(rec: dict, body_max_lines: int) -> dict | None:
    prov = provisional_labels(rec.get("arbiter_log_match"))
    src_path = Path(rec["source"]["transcript"]).name
    src_line = rec["source"]["line_no"]
    ts = rec["source"].get("timestamp") or "(unknown)"
    print()
    print(f"event={rec['event']}  id={rec['id']}  src={src_path}:{src_line}  ts={ts}")
    if rec.get("arbiter_log_match"):
        print(f"arbiter@4B fired: {rec['arbiter_log_match']}")
    _show_body(rec["body_stripped"], body_max_lines)

    body = rec["body_stripped"]
    shown = {"full": False}

    def show_full() -> None:
        if shown["full"]:
            return
        print(body)
        shown["full"] = True

    labels: dict[str, bool] = {}
    for verdict in VERDICTS:
        default = bool(prov.get(verdict)) if prov else False
        result = prompt_label(verdict, default, show_full)
        if result is None:
            print("  skipped")
            return None
        labels[verdict] = result
    return {**rec, "labels": labels}


def label_session(
    records: list[dict], output_path: Path, already: dict[str, dict], body_max_lines: int
) -> None:
    queue = [r for r in records if r["id"] not in already]
    if not queue:
        print(f"all {len(records)} selected records already labeled in {output_path}")
        return
    total = len(records)
    done = total - len(queue)
    print(f"labeling {len(queue)} new records ({done}/{total} already done)")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("a", encoding="utf-8") as out_fh:
        try:
            for idx, rec in enumerate(queue, start=1):
                print()
                print(f"[{done + idx}/{total}]", end=" ")
                labeled = label_one(rec, body_max_lines)
                if labeled is None:
                    continue
                out_fh.write(json.dumps(labeled, ensure_ascii=False) + "\n")
                out_fh.flush()
        except QuitSession:
            print("\nstopping. progress saved.")


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    here = Path(__file__).resolve().parent
    ap.add_argument("--input", type=Path, default=here / "corpus.unlabeled.jsonl")
    ap.add_argument("--output", type=Path, default=here / "corpus.labeled.jsonl")
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
    ap.add_argument(
        "--per-category",
        type=int,
        default=20,
        help="Cap per category for mixed/random/keyword/clear strategies.",
    )
    ap.add_argument(
        "--body-max-lines",
        type=int,
        default=40,
        help="Lines of body to show before truncating with a ?-to-expand hint.",
    )
    ap.add_argument("--seed", type=int, default=17)
    ap.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the selection plan and exit without prompting.",
    )
    args = ap.parse_args()

    if not args.input.exists():
        sys.stderr.write(f"missing input corpus: {args.input}\n")
        return 1

    corpus = load_corpus(args.input)
    rng = random.Random(args.seed)
    selected = select_records(corpus, args.strategy, args.per_category, rng)
    already = load_already_labeled(args.output)

    print(f"corpus size:    {len(corpus)}")
    print(f"strategy:       {args.strategy} (per_category={args.per_category}, seed={args.seed})")
    print(f"selected:       {len(selected)}")
    print(f"already labeled (will skip): {sum(1 for r in selected if r['id'] in already)}")
    print(f"output:         {args.output}")

    if args.dry_run:
        breakdown: dict[str, int] = {}
        for r in selected:
            key = r.get("arbiter_log_match") or "<no-match>"
            breakdown[key] = breakdown.get(key, 0) + 1
        print()
        print("selection breakdown by arbiter_log_match:")
        for k, v in sorted(breakdown.items(), key=lambda kv: -kv[1]):
            print(f"  {v:5d}  {k}")
        return 0

    label_session(selected, args.output, already, args.body_max_lines)
    return 0


if __name__ == "__main__":
    sys.exit(main())
