# Lane entry, lane file, and finish block

Each lane has two parts. The lane entry goes in the plan's Work section and holds what the coordinator acts on. The lane file goes in the run book as `lane-[branch].md` and holds what the lane's worker acts on. One finish block closes the plan's Work section. Replace each square bracket with what it describes, taking each command from `references/worktree-tools.md` for the tool this machine has. Leave each angle-bracketed placeholder, `<worktree>` for one, for the run to fill.

With one lane worked by the plan's one agent, there is no run book: write the entry, then the lane file's body under it in the plan.

## Lane entry, in the plan

```markdown
### Lane [branch] (wave [number])

- worker: [the agent from the Roster]
- units: [the work units this lane holds, in order]
- owns: [each path the lane may change, relative to the root, and, for each path another lane also changes, the functions or regions of it this lane owns; nothing outside them]
- provides: [each contract this lane implements, by name; or none]
- consumes: [each contract this lane builds against, by name; or none]
- waits on: [none, or each lane that lands before this lane's work starts, each with the code of it this lane needs; a file both lanes change makes no wait]
- early start: [none, or "red tests against fixed contracts": create the worktree with wave [number], and message the worker as each awaited lane lands]
- create: from [primary checkout], a new worktree on a new branch [branch] based on [base], leaving the primary checkout's branch as it was: `[create command]`; the absolute path that command reports goes into the worker's prompt as `<worktree>`
- run-book file: [absolute path of `lane-[branch].md`]; hand it to the worker by path, unread
```

## Lane file, in the run book

Under the header `references/run-book.md` gives:

```markdown
- provisioning: [the hook that provisions the worktree as it is created, named with the file that holds it, or the commands to run in `<worktree>` before its first commit]
- owns: [the lane entry's owns line, word for word]
- checks: [the command that runs only the tests this lane adds or changes, through the runner's file or name filter, with its passing result], each run in the foreground; leave unrun the full suite, other lanes' tests, and what the commit hook runs: [the hook's formatter, linter, and type check, by name]
- leave undone: a push; a check, suite, or formatter run over files outside your owns line; an edit outside your owns line, a shared file such as a README or a module holding a contract included, which goes to the coordinator in a message; and an end to your turn while a command you started still runs in the background; and a revert or hand edit of what a formatter or linter changed, since every such change, in a file outside your owns line too, stays as the tool left it and goes into your commit
- skills: [each skill that bears on this lane's task, by exact name, loaded before the first change; or none]
- delegates: [none, or each agent you may spawn, in the order they run, a test writer ahead of the implementation for one]; you write each one's prompt, each works only inside `<worktree>` on this lane's files, and each reports to you
- early start: [none, or: write your red tests as soon as `<worktree>` exists, against the fixed contracts alone; when the coordinator messages that an awaited lane landed, rebase onto [trunk] before the rest]
- commit: through the hooks with `git -C <worktree> add <paths>`, then `git -C <worktree> commit -m '<message>'`, staging with it every file a formatter or linter changed; `git -C <worktree> status --short` prints nothing after each commit
- land, once the checks pass:
  1. Squash the lane's commits since [trunk] into one commit carrying the lane's message: `[squash command]`. Confirm `git -C <worktree> log --oneline [trunk]..HEAD` lists one commit.
  2. Run `git -C <worktree> fetch`, then `git -C <worktree> rev-list --left-right --count [trunk]...[trunk]@{upstream}`. Both counts above zero ? stop and report both counts. [leave this step out where the trunk has no upstream]
  3. Rebase the lane onto [trunk], fast-forward [trunk] to the lane's one commit, and, once the fast-forward holds, remove `<worktree>` and the branch [branch]: `[land command]`[, then `[remove command]`]. The rebase stops on a conflict in a file another lane also changed ? resolve it on its merits, keeping what both lanes changed, and run the lane's checks again before the fast-forward. The trunk moved or the fast-forward was refused ? repeat steps 2 and 3, at most twice more.
  4. Confirm `git -C [primary checkout] log --oneline -1 [trunk]` shows the lane's one commit, and `git -C [primary checkout] worktree list` no longer lists `<worktree>`.
  You alone answer for `<worktree>`: every change, commit, check, and landing step in it is yours. A command you cannot run goes to the coordinator, whole, in a message.
- report: once the lane has landed or a blocker stops it, one final message to the coordinator, opening `landed [SHA] [subject]` or `blocked: [question]`, then what changed, then what the next wave must know. A contract found wrong is reported, never changed.

## Work

[each of the lane's work units in order, as the lines below]

### [unit name]

- makes true:
  - [one behavior per line: what a person or a consuming unit observes once the unit lands, with the command or the observation that shows it]
- owes: [each kind of output beyond the source: tests for each behavior, written and seen failing before the code that passes them; docs; a migration]
- known in advance: [each fact planning found that reading the owned paths would miss; or leave the line out]
- yours to settle: the test cases, and everything inside the owned paths that no contract states
[for a worker on the smallest model, replace "yours to settle" with numbered steps, each with its path, its exact change, and its check]

## Notes
```

## Finish block, in the plan

```markdown
### Finish

- after: every lane lands
- on the primary checkout: [the work that needs every lane, cleanup and deletions for one, or none]
- simplify: [only where the session has a simplify skill: the session's main agent runs it, once, over the source code the lanes landed, `git -C [primary checkout] diff [the trunk commit at planning]..[trunk]`, makes each change it calls for, and commits them on the trunk, before the suites and before any push; landed changes holding only prose get no run]
- suites: [each suite's command, run once on the trunk, with its passing result]
- outcomes: [each "Done when" check on the whole, with its command and passing result]
- report: each lane's landed SHA and subject, from `git -C [primary checkout] log --oneline [trunk]`
```
