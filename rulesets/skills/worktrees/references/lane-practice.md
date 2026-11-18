# Lane practice

You spawn or brief agents that change files, own a lane agent's landing, or clean up worktrees.

## Agents own their worktree and commits

- Give every file-changing subagent its own worktree, created with `wt --yes switch --create`.
- The agent commits there and lands its own lane through `wt merge`, resolving any rebase conflict itself.
- Never run file-changing subagents together in the primary checkout, and never tell one to wait until another commits; a stalled wait was the failure this rule answers.
- Write into the lane prompt: the worktree path and branch, the agent's checks, and the land steps (squash -> fetch -> `wt merge` -> report the SHA).
- Overlapping files are fine: whoever lands second rebases and resolves. A shared file such as a marketplace manifest is no reason to wait.

## Simplify runs in the main session

- A lane agent is the only party responsible for its worktree. It may delegate inside that worktree's scope.
- A sonnet or opus lane agent may spawn its own test writer, which blocks only that lane.
- Leave `simplify` out of lane prompts; the main session runs it once after every planned worktree merges, before any push (see Finish in `SKILL.md`).

## Prune as you go

- Run `wt prune` after every landing, preview with `-n`, in every repository. Put it in every lane agent's land steps after its `wt merge`.
- Keep the default `--min-age`.
- Each worktree holds its own `node_modules`, `.venv`, and build output, so a few left behind cost gigabytes of disk.
- Remove worktrees only as the Every worktree section of `SKILL.md` directs.

## Delete a stale branch or worktree

A stale branch carries old copies of content that has since moved or changed, so taking from it surfaces conflicting copies. Take nothing from it.

- Delete a stale branch or worktree only on confirmation -> `git bundle` verified with `git bundle verify` -> a tarball of its untracked files -> delete.
- The superseded worktree block in `SKILL.md` gives the bundle and removal commands.
