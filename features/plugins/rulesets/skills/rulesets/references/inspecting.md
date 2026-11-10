# Inspecting

Required reading: [Commands](../../../docs/commands.md), the sections on `explain`, `render`, and
`render --check`.

None of these cases changes a file under `ROOT`, apart from `CLI render` with no `--out`, which
rewrites `ROOT/-render/`.

A context is named by its facts: `--model`, `--agent`, `--kind session` or `--kind delegate`,
`--tools TOOL`, and `--flag NAME`, each repeatable where it is a list. A fact left out is absent,
and flags left out are unset. To name a context that already ran, read its facts from its delivery
record (runtime reference, case 21).

## 15. One context's full set of rules

1. Run `RUN CLI render --root ROOT --out FILE` with the context's facts, `FILE` a path outside
   `ROOT`.
2. Read `FILE`. It holds each rule the context receives, sorted by name, under a marker line
   `<!-- rule: NAME -->`, or `<!-- rule: NAME variant: VARIANT -->` for a variant. A withheld rule
   is left out.

## 16. Why a context got or missed a rule

1. Run `RUN CLI explain NAME --root ROOT` with the context's facts.
2. Report the two attributes it prints, inclusion and variant: the winning line, with file and
   line, and the lines it beat.
3. Where explain shows the rule included and the context still lacks it, run
   `RUN CLI check --root ROOT`: delivery withholds a rule whose file carries an error.
4. Where it exits 1, the pool holds no rule of that name.

## 17. What an edit changes across every context

1. Before the edit: `RUN SCRIPTS/impact.py snapshot --root ROOT --out BEFORE`, `BEFORE` a new
   directory.
2. After it: the same into `AFTER`, then `RUN SCRIPTS/impact.py diff BEFORE AFTER`.
3. The diff prints a context's facts, `kind=… model=… agent=… flag=… tools=…`, then one line per
   rule that changed: `+ NAME` added, `- NAME` removed, `~ NAME: WAS -> NOW` set to another
   variant, `default` naming the default form. A context with no change prints nothing.

The matrix crosses each kind, each declared model and none, each agent a condition tests and none,
no flag and each declared flag alone, and no tool and each tool a condition tests. A context
outside it, two flags at once for one, needs `explain` or `render --out`.

## 18. The gate before a commit

Run `RUN SCRIPTS/gate.py --root ROOT`. It runs `check`, then `render --check`, writes nothing, and
stops at the first step that fails, printing `gate: stopped at STEP`.

- Stopped at `check`: clear every error line above the stop (rules reference, case 7, for the
  warnings; an error names its kind, file, and line). A warning alone never stops the gate.
- Stopped at `render --check`: the render tree is stale. Run `RUN CLI render --root ROOT`, then
  the gate again.
- `gate: passed check and render --check`: the directory is ready to commit.
