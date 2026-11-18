# Lane entry, lane file, and finish block

Each lane has two parts. The lane entry goes in the plan's Work section and holds what the coordinator acts on. The lane file goes in the run book as `lane-[branch].md` and holds what the lane's worker acts on. One finish block closes the plan's Work section. Replace each square bracket with what it describes. Leave each angle-bracketed placeholder, `<worktree>` for one, for the run to fill. Neither part holds a command that creates, commits in, lands, or removes a worktree: the `worktrees` skill holds those, and both parts send their reader to it.

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
- base: [the branch the lane's worktree is created from, the trunk or the lane's branch it stacks on]; create the worktree from [primary checkout] on a new branch [branch] as the `worktrees` skill directs, and put the absolute path it reports into the worker's prompt as `<worktree>`
- run-book file: [absolute path of `lane-[branch].md`]; hand it to the worker by path, unread
```

## Lane file, in the run book

Under the header `references/run-book.md` gives:

```markdown
- provisioning: [the commands that install what this lane's checks need, run in `<worktree>` before its first commit where no hook of the repository provisions a new worktree; or none]
- owns: [the lane entry's owns line, word for word]
- checks: [the command that runs only the tests this lane adds or changes, through the runner's file or name filter, with its passing result], each run in the foreground; leave unrun the full suite, other lanes' tests, and what the commit hook runs: [the hook's formatter, linter, and type check, by name]
- leave undone: a push; a check, suite, or formatter run over files outside your owns line; an edit outside your owns line, a shared file such as a README or a module holding a contract included, which goes to the coordinator in a message; and an end to your turn while a command you started still runs in the background; and a revert or hand edit of what a formatter or linter changed, since every such change, in a file outside your owns line too, stays as the tool left it and goes into your commit
- skills: `worktrees`, loaded through the Skill tool before the first change[, then each other skill that bears on this lane's task, by exact name]
- delegates: [none, or each agent you may spawn, in the order they run, a test writer ahead of the implementation for one]; you write each one's prompt, each works only inside `<worktree>` on this lane's files, and each reports to you
- early start: [none, or: write your red tests as soon as `<worktree>` exists, against the fixed contracts alone; when the coordinator messages that an awaited lane landed, bring the lane onto [trunk] as the `worktrees` skill directs before the rest]
- commit and land: as the `worktrees` skill directs for an assigned worktree, with `<worktree>` as that worktree, [branch] as its branch, [trunk] as the branch it lands on, and [primary checkout] as the primary checkout; land once the checks pass. You alone answer for `<worktree>`: every change, commit, check, and landing step in it is yours. A command you cannot run goes to the coordinator, whole, in a message.
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
