# Example: a coordinated plan

Three features that would each have edited one render file in turn. The size pass answered several units; fixing three contracts took every feature's logic out of the render file, which left one hotspot for one integrator. The plan runs as three waves: a contracts unit alone, three module lanes at once with a researcher beside them, then the integrator. The machine had git and no other worktree tool, a pre-commit hook that type-checks, and a `make` file.

To stay short, this example writes one lane block in full and elides the other three, and leaves out Tooling, Invitations, and Verification. A real plan writes every block whole.

**Example 2:**

Input: "Plan the usage meter work: a colour per category, light and dark palettes, and a setting to pick one. Get as much of it as possible running at once."

Output:

````markdown
# Usage meter: named categories, light and dark palettes, a theme setting

Goal: the usage meter under the prompt shows every category in a colour of its own, in a light or dark palette the person picks, with `make test` passing on `main`.

Shape: 5 units in 3 waves. You coordinate and implement nothing; 4 workers and 1 researcher work in lanes created with `git worktree`.

## Glossary

- root: `/work/term-app`, the primary checkout; relative paths resolve against it, or against `<worktree>` inside a lane
- trunk: `main`, at `9e2f1c0` when this plan was written
- meter: the one-line bar under the prompt showing what fills the session's memory, drawn by `src/meter/render.tsx`
- category: one kind of content the meter counts, such as file reads or replies
- hotspot: `src/meter/render.tsx`, which every feature here would otherwise edit

## Target outcomes

- As an engineer glancing under the prompt mid-task, I want each category in a colour of its own, so that I can tell what fills the session without reading the legend.
  - Done when: `make test-meter` passes its "no two categories share a colour" case for both palettes.
- As an engineer working in a light terminal, I want to pick the light palette once, so that the meter stays readable without my changing terminal themes.
  - Done when: with `meter.theme = "light"` in the app config, `make meter-snapshot` prints the light palette's colours.
- As the engineer who started this run and stepped away, I want each lane to end in one message, landed or blocked on a named question, so that I return to a finished trunk or a single decision.
  - Done when: your final report lists four landed commits, or one blocked lane with its question.

## Perspective

You are the coordinator. You create worktrees, start agents, relay messages, and run the finish. Every change to a source file belongs to a worker.

## Contracts

All fixed. Declared in `src/meter/contracts.ts`, owned by the unit `contracts`.

### CategoryId and categorize

- owner: `src/meter/categories.ts`, unit `categories`
- consumers: `palette`, `render`
- status: fixed

```ts
export type CategoryId = "system" | "tools" | "reads" | "writes" | "replies" | "other"
export function categorize(row: MeterRow): CategoryId // total: every row maps to one id, unknown rows to "other"
```

### Theme and readTheme

- owner: `src/meter/settings.ts`, unit `theme`
- consumers: `render`
- status: fixed

```ts
export type Theme = "light" | "dark"
export function readTheme(config: AppConfig): Theme // "dark" when meter.theme is absent or unrecognised; never throws
```

### Palette and paletteFor

- owner: `src/meter/palette.ts`, unit `palette`
- consumers: `render`
- status: fixed

```ts
export type Palette = Readonly<Record<CategoryId, string>> // "#rrggbb", no two ids sharing a value
export function paletteFor(theme: Theme): Palette
```

## Coordination

### Roster

| agent | role | type and model | owns | starts in | reports to |
| --- | --- | --- | --- | --- | --- |
| you | coordinator | the session's main agent | this plan | wave 1 | the person who approved it |
| contracts-worker | worker | general-purpose, mid-sized model | lane `meter-contracts` | wave 1 | you |
| palette-worker | worker | general-purpose, mid-sized model | lane `meter-palette` | wave 2 | you |
| theme-worker | worker | general-purpose, mid-sized model | lane `meter-theme` | wave 2 | you |
| categories-worker | worker | general-purpose, mid-sized model | lane `meter-categories` | wave 2 | you |
| label-researcher | researcher | general-purpose, smallest model | the question below | wave 2 | you |
| render-worker | integrator | general-purpose, strongest model | lane `meter-render` | wave 3 | you |

### Shared conventions

- Commit messages: `feat(meter): <what changed>`, lowercase, no trailing period.
- Colours are lowercase `#rrggbb` strings.
- Import contract types from `src/meter/contracts.ts`, never from another lane's module.

### Waves

Wave 1: `contracts`

1. before: `make test` passes on `main`.
2. create: `git -C /work/term-app worktree add -b meter-contracts /work/term-app-meter-contracts main`, then `make install` in that worktree.
3. start: contracts-worker, in the background. Its prompt: the Roster in a `<roster>` tag, Shared conventions in a `<conventions>` tag, then the lane block `meter-contracts` in a `<block>` tag. Every later prompt takes the same shape.
4. while it runs: wait for its report.
5. ends when: contracts-worker reports landed, and `git -C /work/term-app log --oneline -1 main` shows its commit.

Wave 2: `palette`, `theme`, `categories`, and the researcher

1. before: wave 1 ended.
2. create: one worktree per lane from `main` as it now stands, by the same two commands, for `meter-palette`, `meter-theme`, and `meter-categories`.
3. start: the three workers and label-researcher, all in one message, each in the background. The researcher's prompt: "List every assertion in `tests/meter/render.test.tsx` that names a category label or a colour, with its line and the exact string asserted. Write the list to `/work/term-app-notes/render-assertions.md`. Change no other file."
4. while they run: wait for reports, and act only by the Messages table.
5. ends when: all three workers report landed, the researcher's file exists, and `make test` passes on `main`.

Wave 3: `render`

1. before: wave 2 ended.
2. create: the worktree for `meter-render` from `main` as it now stands.
3. start: render-worker, with its lane block, the Roster, Shared conventions, and the path of the researcher's file.
4. while it runs: wait for its report.
5. ends when: render-worker reports landed. Then run the Finish block.

### Messages

| event | from | to | holds |
| --- | --- | --- | --- |
| a lane lands | its worker | you | `landed <SHA> <subject>`, and each contract it implemented as stated |
| a worker finds a contract wrong | that worker | you | the contract's name, the conflict, the change it proposes; that part of its work stops |
| a contract is amended | you | every worker providing or consuming it | the amended statement, quoted from this plan |
| a worker is blocked | that worker | you | one question, with the options it would choose among |
| the researcher finishes | label-researcher | you | the path of its file and the number of assertions listed |

### Escalation

A question this plan does not answer: stop that worker only, keep the others running, and put the question to the person who approved the plan, with the options and what each commits the run to. Never decide alone a change to a contract's meaning, a change to which lane owns a file, or dropping a target outcome.

## Work

### Lane meter-palette (wave 2)

- read first: this plan at `/work/term-app-notes/plan.md`: Glossary, Constraints, and the contracts CategoryId and Palette
- worktree: the coordinator creates it as wave 2 starts, from `/work/term-app`, as a new worktree on a new branch `meter-palette` based on `main`: `git -C /work/term-app worktree add -b meter-palette /work/term-app-meter-palette main`; written `<worktree>` below
- provisioning: `make install`, run in `<worktree>` before its first commit
- owns: `src/meter/palette.ts`, `tests/meter/palette.test.ts`; nothing outside them
- provides: Palette and paletteFor
- consumes: CategoryId
- checks: `make test-meter` passes; the pre-commit hook runs the formatter and `tsc`
- skills: none
- worker: palette-worker; it alone answers for `<worktree>`
- delegates: none
- waits on: lane `meter-contracts`, for the declarations in `src/meter/contracts.ts`
- early start: none
- commit: through the hooks with `git -C <worktree> commit -m '<message>' -- <paths>`; `git -C <worktree> status --short` prints nothing after each commit
- land, once the checks pass:
  1. Squash into one commit: `git -C <worktree> reset --soft "$(git -C <worktree> merge-base main HEAD)"`, then `git -C <worktree> commit -m 'feat(meter): add light and dark palettes'`. Confirm `git -C <worktree> log --oneline main..HEAD` lists one commit.
  2. `git -C <worktree> rebase main`, then `git -C /work/term-app merge --ff-only meter-palette`, then `git -C /work/term-app worktree remove <worktree>` and `git -C /work/term-app branch -d meter-palette`. A conflict stops the rebase ? resolve it keeping both lanes' changes, and run the checks again. `main` moved ? repeat this step, at most twice more.
  3. Confirm `git -C /work/term-app log --oneline -1 main` shows the commit, and `git -C /work/term-app worktree list` no longer lists `<worktree>`.
- report: one final message to the coordinator, opening `landed <SHA> <subject>` or `blocked: <question>`. A contract found wrong is reported, never changed.
- work:

  | path | symbol | change |
  | --- | --- | --- |
  | `src/meter/palette.ts` | `paletteFor` | return the light or dark table; six colours each, all distinct |
  | `tests/meter/palette.test.ts` | new | for each theme: every `CategoryId` has a colour, and no two share one |

  - test first: both cases fail against the stub, which throws `not implemented`.

[lanes `meter-contracts`, `meter-theme`, `meter-categories`, and `meter-render` follow, each a full block; elided in this example]

### Finish

- after: every lane lands
- on the primary checkout: delete `src/meter/legacy-colours.ts`, which nothing imports once `meter-render` lands; its own commit
- suites: `make test`, once on `main`: every suite passes
- outcomes: `make meter-snapshot` with `meter.theme = "light"` prints the light palette's colours
- report: each lane's landed SHA and subject, from `git -C /work/term-app log --oneline main`

## Constraints

- No lane changes a fixed contract. A worker that finds one wrong stops that part of its work and reports it.
- Every commit goes through the pre-commit hook. A rejection is the next task.
- Nothing is pushed.
````

</example>
