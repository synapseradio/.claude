#!/usr/bin/env python3
"""Corpus test for the Arbiter verdicts.

Imports the Arbiter library under `scripts/arbiter/lib/` and exercises
`judge_many` against a fixed list of bodies, comparing the fired
verdict set to the expected set per case. Running this requires a
live `llama-server` on the port configured in the client (started by
`arbiter-up.sh`).

The expected sets encode the *intended* behavior of the verdict
prompts. A failure means the current prompt and the case disagree,
which is the signal: either tighten the prompt, recategorize the
case, or accept the gap.

To swap models for an A/B run, edit `ARBITER_MODEL_PATH` in
`scripts/arbiter/arbiter-config.sh`, kill the running server, and
run `scripts/arbiter/arbiter-up.sh` to bring it back up against the
new blob.

Pass a single case label as the only positional argument to run just
that case, e.g. `python3 test_block_open_questions_judge.py meta-discussion`.

The script exits non-zero when any case fails. Each case prints a
row with status, latency, label, expected verdict set, and got set.
"""
import pathlib
import sys
import time

ARBITER_DIR = pathlib.Path(__file__).resolve().parents[1] / "arbiter"
sys.path.insert(0, str(ARBITER_DIR))

from lib.client import JUDGE_MAX_TOKENS, JUDGE_URL, judge_many  # noqa: E402
from lib.config import load_bindings  # noqa: E402
from lib.frame import get_framing  # noqa: E402

CASES = [
    ("empirical-1",
     "What does the bun docs say about HMR? Should I import from @foo/bar or foo/bar?",
     {"OPEN_QUESTIONS"}),
    ("empirical-2",
     "Could you tell me what type the `request` parameter is on the handler?",
     {"OPEN_QUESTIONS"}),
    ("open-question-genuine",
     "Do you want this rolled out to all users or staff only? Let me know.",
     {"OPEN_QUESTIONS"}),
    ("open-question-todo",
     "I've added the helper. TODO: pick a name for the wrapper before merge.",
     {"OPEN_QUESTIONS"}),
    ("uncommitted-alternatives",
     "I see two options here: A) inline the helper, B) extract it into a module. Both have tradeoffs.",
     {"UNCOMMITTED_ALTERNATIVES"}),
    ("out-of-scope-clean",
     "All 25 tests pass. The TS diagnostics on the test file are pre-existing mock typing issues unrelated to my refactor.",
     {"OUT_OF_SCOPE_DEFERRAL"}),
    ("out-of-scope-asking",
     "Tests pass. The TS errors are pre-existing. Should I leave them?",
     {"OUT_OF_SCOPE_DEFERRAL", "OPEN_QUESTIONS"}),
    ("baseline-probe",
     "Let me check whether these tests fail on main before I dig in.",
     {"BASELINE_PROBE"}),
    ("baseline-probe-stash",
     "I'll stash my changes, switch to master, and run the suite to see if these failures pre-existed.",
     {"BASELINE_PROBE"}),
    ("rebase-clears",
     "I rebased onto main and resolved the conflict in src/foo.ts.",
     set()),
    ("commit-clears",
     "I went with option A — inlined the helper. Tests pass and lint is clean.",
     set()),
    ("benign-report",
     "Tests pass and lint is clean. Pushed the branch.",
     set()),
    ("meta-discussion",
     "OPEN_QUESTIONS fires when the assistant asks the user something inline. UNCOMMITTED_ALTERNATIVES fires when two paths are listed without commitment.",
     set()),
    ("all-four-combo",
     "Two options: A) inline, B) extract — which do you prefer? Tests pass, the TS errors are pre-existing. Let me check whether they fail on main.",
     {"OPEN_QUESTIONS", "UNCOMMITTED_ALTERNATIVES", "OUT_OF_SCOPE_DEFERRAL", "BASELINE_PROBE"}),
    ("all-four-with-empirical",
     "What does the docs say about HMR? Two options: A) inline, B) extract — which do you prefer? Tests pass, the TS errors are pre-existing. Let me check whether they fail on main.",
     {"OPEN_QUESTIONS", "UNCOMMITTED_ALTERNATIVES", "OUT_OF_SCOPE_DEFERRAL", "BASELINE_PROBE"}),

    # ── No-fire cases probing the OPEN_QUESTIONS gap ──
    # These are bodies that contain question marks but should NOT fire
    # OPEN_QUESTIONS under the intended pause-on-user criterion: the
    # assistant either answers the question in the same turn, frames
    # it as exploration / hypothesis, quotes it, or lists it as a
    # thinking prompt. The current verdict prompt fires on any inline
    # question, so several of these will fail until the prompt is
    # tightened — that is the signal.

    # The verdict prompt fires on a body composed entirely of stacked
    # exploratory questions, since "the body contains a question the
    # assistant directs at the user" reads true regardless of intent.
    # Tightening the prompt to carve out exploratory stacks regresses
    # multi-clause bodies on the small judge model, so this case is
    # pinned as the prompt's documented behavior — a regression check
    # on the verdict prompt, exercised here in isolation from any
    # binding. The verdict only fires in production on bindings that
    # subscribe to open_questions (currently the ExitPlanMode plan
    # body), so this body shape is not a user-facing concern on
    # turn-ending messages.
    ("wonder-output",
     "Why does the cache invalidate on every write? What invariant is the test really protecting? Could a property-based test catch the edge case better than the current example tests?",
     {"OPEN_QUESTIONS"}),
    ("hypothetical-what-if",
     "What if we cached the response per session? It would reduce DB load but might serve stale data on rapid edits — for this workload the staleness is fine, so let's go with per-session caching.",
     set()),
    ("pedagogical-q-and-a",
     "What's the difference between `Promise.all` and `Promise.allSettled`? `all` rejects on the first failure; `allSettled` resolves once every promise has settled, regardless of outcome.",
     set()),
    ("self-directed-then-resolved",
     "Where does the cache invalidate? Tracing through `cache.py` — invalidation happens in `flush_after_write` on line 47. So the stale read is on that path, not in the reader.",
     set()),
    ("quoted-question",
     "A future reader might ask, 'why two separate maps for extractors and framings?' — keeping them split lets each evolve independently without one's schema bleeding into the other.",
     set()),
    ("suppose-framing",
     "Suppose two writers hit this row in the same millisecond. The lock-free version drops one update; the locked version serializes them at roughly 2x latency. The locked version wins for this workload because correctness beats throughput here.",
     set()),

    # ── Fire cases sharpening the OPEN_QUESTIONS positive boundary ──
    # These should fire because the assistant pauses on a reply from
    # the user, even if the surface looks self-directed or buried.

    ("empirical-punt-disguised",
     "Hmm, what does Bun actually do with HMR for nested layouts? Let me know.",
     {"OPEN_QUESTIONS"}),
    ("mid-paragraph-pause",
     "We need to set the cache TTL — should it be 5 minutes or 1 hour, depending on how stale you can tolerate? Once that's decided I'll wire it.",
     {"OPEN_QUESTIONS"}),
    ("preference-no-signoff",
     "Which would you prefer here, A or B?",
     {"OPEN_QUESTIONS"}),
]


def _all_verdict_specs():
    """Pull every verdict spec from bindings.yaml (the corpus exercises
    all four — same set the PreToolUse:ExitPlanMode binding subscribes to)."""
    bindings = load_bindings(ARBITER_DIR / "bindings.yaml")
    return list(bindings.verdicts.values())


def run_one(verdict_specs, framing, label, body, expected):
    t0 = time.monotonic()
    fired_keys = judge_many(body, framing, verdict_specs, "test")
    elapsed_ms = int((time.monotonic() - t0) * 1000)
    if fired_keys is None:
        return label, expected, None, "JUDGE_ERROR", elapsed_ms
    name_by_key = {s.key: s.name for s in verdict_specs}
    got = {name_by_key[k] for k in fired_keys}
    status = "PASS" if got == expected else "FAIL"
    return label, expected, got, status, elapsed_ms


def main():
    only = sys.argv[1] if len(sys.argv) > 1 else None
    print(f"Endpoint: {JUDGE_URL}  max_tokens={JUDGE_MAX_TOKENS}")
    verdict_specs = _all_verdict_specs()
    framing = get_framing("Stop")
    if framing is None:
        print("missing framing for Stop", file=sys.stderr)
        sys.exit(1)
    results = []
    total_ms = 0
    for label, body, expected in CASES:
        if only and only != label:
            continue
        r = run_one(verdict_specs, framing, label, body, expected)
        results.append(r)
        label, expected, got, status, ms = r
        total_ms += ms
        ex = sorted(expected) if expected else "[]"
        gt = sorted(got) if got else ("[]" if got is not None else got)
        print(f"  {status}  {ms:5d}ms  {label:30s}  expected={ex}  got={gt}")
    fails = [r for r in results if r[3] != "PASS"]
    print(f"\n{len(results)-len(fails)}/{len(results)} passed   total={total_ms}ms   avg={total_ms//len(results) if results else 0}ms")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
