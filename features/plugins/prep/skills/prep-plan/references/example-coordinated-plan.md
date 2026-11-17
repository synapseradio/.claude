# Example: a coordinated plan

Three features that would each have edited one render file in turn. The size pass answered several units; fixing three contracts took every feature's logic out of the render file, which left one hotspot for one integrator. The plan runs as three waves: a contracts unit alone, three module lanes at once with a researcher beside them, then the integrator. The machine had git and no other worktree tool, a pre-commit hook that type-checks, and a `make` file. The session's agent list held `prep:work-coordinator`.

The plan file holds what the coordinator acts on and what every agent shares. Each worker's material sits in the run book beside it, one file per reader. To stay short, this example writes one lane entry and one lane file in full and elides the others, and leaves out Tooling, Invitations, and Verification. A real plan writes every entry and every file whole.

**Example 2:**

Input: "Plan the usage meter work: a colour per category, light and dark palettes, and a setting to pick one. Get as much of it as possible running at once."

Output, the plan file at `/work/term-app-notes/usage-meter.md`:

````markdown
# Usage meter: named categories, light and dark palettes, a theme setting

Goal: the usage meter under the prompt shows every category in a colour of its own, in a light or dark palette the person picks, with `make test` passing on `main`.

Run: the session's main agent starts `prep:work-coordinator` once, in the background, with this file's absolute path, then answers what the coordinator hands up and changes no file this plan covers. From the next line on, "you" is that coordinator.

Shape: 5 units in 3 waves. You coordinate and implement nothing; 4 workers and 1 researcher work in lanes created with `git worktree`.

## Glossary

- root: `/work/term-app`, the primary checkout; relative paths resolve against it, or against `<worktree>` inside a lane
- trunk: `main`, at `9e2f1c0` when this plan was written
- run book: `/work/term-app-notes/usage-meter.runbook/`, one file per worker; you hand each over by path and open none
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

You are the coordinator. You create worktrees, start agents, relay messages, and run the finish. Every change to a source file belongs to a worker, and every worker's instructions sit in its run-book file.

## Module map

```text
modules: [name] is a unit this plan changes, (name) is code it leaves alone
  [contracts]   src/meter/contracts.ts     wave 1
  [categories]  src/meter/categories.ts    wave 2
  [theme]       src/meter/settings.ts      wave 2
  [palette]     src/meter/palette.ts       wave 2
  [render]      src/meter/render.tsx       wave 3
  (config)      src/config.ts              unchanged

relations: provider --> consumer : contract, and the data that crosses
  [contracts]  --> [categories] [theme] [palette] [render] : the type declarations below
  [categories] --> [palette] : CategoryId, the six ids
  [categories] --> [render]  : categorize, MeterRow in, CategoryId out
  [theme]      --> [render]  : readTheme, AppConfig in, Theme out
  [palette]    --> [render]  : paletteFor, Theme in, Palette out
  (config)     --> [theme]   : AppConfig, read only
```

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

Run-book files sit in `/work/term-app-notes/usage-meter.runbook/`.

| agent | role | type, model, effort | owns | starts in | reports to | run-book file |
| --- | --- | --- | --- | --- | --- | --- |
| you | coordinator | `prep:work-coordinator` | this plan | wave 1 | the session's main agent | none |
| contracts-worker | worker | harness default, sonnet, low | lane `meter-contracts` | wave 1 | you | `lane-meter-contracts.md` |
| palette-worker | worker | harness default, sonnet, medium | lane `meter-palette` | wave 2 | you | `lane-meter-palette.md` |
| theme-worker | worker | harness default, sonnet, medium | lane `meter-theme` | wave 2 | you | `lane-meter-theme.md` |
| categories-worker | worker | harness default, sonnet, medium | lane `meter-categories` | wave 2 | you | `lane-meter-categories.md` |
| label-researcher | researcher | harness default, haiku, low | the assertion list | wave 2 | you | `agent-label-researcher.md` |
| render-worker | integrator | harness default, opus, medium | lane `meter-render` | wave 3 | you | `lane-meter-render.md` |

### Shared conventions

- Commit messages: `feat(meter): <what changed>`, lowercase, no trailing period.
- Colours are lowercase `#rrggbb` strings.
- Import contract types from `src/meter/contracts.ts`, never from another lane's module.

### Prompts

Each agent's prompt holds a greeting naming its role, the Roster in a `<roster>` tag, Shared conventions in a `<conventions>` tag, its `<worktree>` path, and the line "Read [its run-book file's absolute path] first; it holds your work." Hand each run-book file over by path, unread.

### Waves

Wave 1: `contracts`

1. before: `make test` passes on `main`.
2. create: the `create` command of lane `meter-contracts`.
3. start: contracts-worker, in the background.
4. while it runs: wait for its report.
5. ends when: contracts-worker reports landed, and `git -C /work/term-app log --oneline -1 main` shows its commit.

Wave 2: `palette`, `theme`, `categories`, and the researcher

1. before: wave 1 ended.
2. create: the `create` command of each of the three lanes, from `main` as it now stands.
3. start: the three workers and label-researcher, all in one message, each in the background.
4. while they run: wait for reports, and act only by the Messages table.
5. ends when: all three workers report landed, the researcher reports its file written, and `make test` passes on `main`.

Wave 3: `render`

1. before: wave 2 ended.
2. create: the `create` command of lane `meter-render`, from `main` as it now stands.
3. start: render-worker, adding to its prompt the path the researcher reported.
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
| a decision exceeds this plan | you | the session's main agent | one question, the options, what each commits the run to, and which lanes wait on it |

### Escalation

A worker's question inside its own paths, where its checks catch a wrong answer: tell the worker it is the worker's to settle. A question a read or a command settles: have it read or run, and answer. A change to a contract's meaning, to which lane owns a file, or to the order of waves: stop that worker only, keep the others running, and put the question to the session's main agent. Dropping a target outcome, or any push: the same message, marked as a person's to settle.

## Work

### Lane meter-palette (wave 2)

- worker: palette-worker
- units: `palette`
- owns: `src/meter/palette.ts`, `tests/meter/palette.test.ts`; nothing outside them
- provides: Palette and paletteFor
- consumes: CategoryId
- waits on: lane `meter-contracts`, for the declarations in `src/meter/contracts.ts`
- early start: none
- create: `git -C /work/term-app worktree add -b meter-palette /work/term-app-meter-palette main`; the path `/work/term-app-meter-palette` goes into the worker's prompt as `<worktree>`
- run-book file: `/work/term-app-notes/usage-meter.runbook/lane-meter-palette.md`; hand it to the worker by path, unread

[lane entries `meter-contracts`, `meter-theme`, `meter-categories`, and `meter-render` follow, each in the same form; elided in this example]

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

The run-book file at `/work/term-app-notes/usage-meter.runbook/lane-meter-palette.md`:

````markdown
# meter-palette: the light and dark colour tables

- reader: palette-worker
- not needed by: the coordinator and every other agent; each works from the plan alone
- plan: `/work/term-app-notes/usage-meter.md`; read its Glossary, Constraints, Shared conventions, and the contracts CategoryId and Palette before the rest of this file
- filled by your prompt: `<worktree>`

- provisioning: `make install`, run in `<worktree>` before its first commit
- owns: `src/meter/palette.ts`, `tests/meter/palette.test.ts`; nothing outside them
- checks: `make test-meter FILE=tests/meter/palette.test.ts` passes; leave unrun `make test`, other lanes' tests, and the formatter and `tsc`, which the pre-commit hook runs
- skills: none
- delegates: none
- early start: none
- commit: through the hooks, with `git -C <worktree> add <paths>` naming your owns-line paths and every file a formatter or linter changed -> confirm `git -C <worktree> diff --cached --name-only` lists only them -> `git -C <worktree> commit -m '<message>'`, with no pathspec; `git -C <worktree> status --short` prints nothing after each commit
- land, once the checks pass:
  1. Squash into one commit: `git -C <worktree> reset --soft "$(git -C <worktree> merge-base main HEAD)"`, then `git -C <worktree> commit -m 'feat(meter): add light and dark palettes'`. Confirm `git -C <worktree> log --oneline main..HEAD` lists one commit.
  2. `git -C <worktree> rebase main`, then `git -C /work/term-app merge --ff-only meter-palette`, then `git -C /work/term-app worktree remove <worktree>` and `git -C /work/term-app branch -d meter-palette`. A conflict stops the rebase ? resolve it keeping both lanes' changes, and run the checks again. `main` moved ? repeat this step, at most twice more.
  3. Confirm `git -C /work/term-app log --oneline -1 main` shows the commit, and `git -C /work/term-app worktree list` no longer lists `<worktree>`.
  You alone answer for `<worktree>`. A command you cannot run goes to the coordinator, whole, in a message.
- report: one final message to the coordinator, opening `landed <SHA> <subject>` or `blocked: <question>`. A contract found wrong is reported, never changed.

## Work

### palette

- makes true:
  - `paletteFor("light")` and `paletteFor("dark")` each return a colour for every `CategoryId`; `make test-meter` shows it
  - within one palette no two categories share a colour; `make test-meter` shows it
- owes: tests for each behavior in `tests/meter/palette.test.ts`, written and seen failing against the stub before the code that passes them
- known in advance: the stub the contracts lane lands throws `not implemented`, so every new test fails for that reason first
- yours to settle: the test cases, the colours themselves, and everything inside the owned paths that no contract states

## Notes
````

</example>
