# Lane block and finish block

One lane block per lane, then one finish block. Replace each square bracket with what it describes, taking each command from `references/worktree-tools.md` for the tool this machine has. Leave each angle-bracketed placeholder, `<worktree>` for one, for the run to fill. A lane block is handed whole to the lane's worker as the core of its prompt.

```markdown
### Lane [branch] (wave [number])

- read first: this plan at [absolute path]: Glossary, Constraints, and the contracts named here
- worktree: the coordinator creates it as wave [number] starts, from [primary checkout], as a new worktree on a new branch [branch] based on [base], leaving the primary checkout's branch as it was: `[create command]`; the absolute path that command reports is written `<worktree>` below
- provisioning: [the hook that provisions the worktree as it is created, named with the file that holds it, or the commands to run in `<worktree>` before its first commit]
- owns: [each path the lane may change, relative to the root, and, for each path another lane also changes, the functions or regions of it this lane owns; nothing outside them]
- provides: [each contract this lane implements, exactly as the plan states it; or none]
- consumes: [each contract this lane builds against, changing none; or none]
- checks: [each command to run before each commit, with its passing result, or the commit hook that runs it]
- skills: [each skill that bears on this lane's task, by exact name, loaded before the first change; or none]
- worker: [the agent from the Roster, or you]; the worker alone answers for `<worktree>`, and every change, commit, check, and landing step in it is the worker's
- delegates: [none, or each agent the worker may spawn, in the order they run]; the worker writes each one's prompt, each works only inside `<worktree>` on this lane's files, and each reports to the worker
- waits on: [none, or each lane that lands before this lane's work starts, each with the code of it this lane needs; a file both lanes change makes no wait]
- early start: [none, or the red tests this lane writes as soon as its worktree exists, against fixed contracts alone; the coordinator messages the worker as each awaited lane lands, and the worker rebases onto [trunk] before the rest]
- commit: through the hooks with `git -C <worktree> commit -m '<message>' -- <paths>`; `git -C <worktree> status --short` prints nothing after each commit
- land, once the checks pass:
  1. Squash the lane's commits since [trunk] into one commit carrying the lane's message: `[squash command]`. Confirm `git -C <worktree> log --oneline [trunk]..HEAD` lists one commit.
  2. Run `git -C <worktree> fetch`, then `git -C <worktree> rev-list --left-right --count [trunk]...[trunk]@{upstream}`. Both counts above zero ? stop and report both counts. [leave this step out where the trunk has no upstream]
  3. Rebase the lane onto [trunk], fast-forward [trunk] to the lane's one commit, and, once the fast-forward holds, remove `<worktree>` and the branch [branch]: `[land command]`[, then `[remove command]`]. The rebase stops on a conflict in a file another lane also changed ? resolve it on its merits, keeping what both lanes changed, and run the lane's checks again before the fast-forward. The trunk moved or the fast-forward was refused ? repeat steps 2 and 3, at most twice more.
  4. Confirm `git -C [primary checkout] log --oneline -1 [trunk]` shows the lane's one commit, and `git -C [primary checkout] worktree list` no longer lists `<worktree>`.
  The worker runs every step itself. A worker that cannot run these commands hands each one to the coordinator.
- report: one final message to [the coordinator], opening `landed [SHA] [subject]` or `blocked: [question]`, then what changed, then what the next wave must know. A contract found wrong is reported, never changed.
- work:
  [the lane's work units in order, each as a table of path, symbol, and change, with its test first and its check]
```

```markdown
### Finish

- after: every lane lands
- on the primary checkout: [the work that needs every lane, cleanup and deletions for one, or none]
- simplify: [only where the session has a simplify skill: you run it yourself, once, over the source code the lanes landed, `git -C [primary checkout] diff [the trunk commit at planning]..[trunk]`, make each change it calls for, and commit them on the trunk, before the suites and before any push; landed changes holding only prose get no run]
- suites: [each suite's command, run once on the trunk, with its passing result]
- outcomes: [each "Done when" check on the whole, with its command and passing result]
- report: each lane's landed SHA and subject, from `git -C [primary checkout] log --oneline [trunk]`
```
