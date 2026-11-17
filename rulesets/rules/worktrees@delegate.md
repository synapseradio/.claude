## worktrees

For every worktree your prompt assigns you, optimize for a branch that reaches its merge as one commit, with every other worktree and branch as you found it.

Leave every worktree and branch your prompt neither assigns nor names untouched and unmentioned.
Keep `skill:simplify` out of the assigned worktree's work, since the session's main agent runs it once after every planned worktree merges.
Run the tests covering the files your work changes, in the foreground, and leave every full test suite to the session's main agent, which runs each once after every planned worktree merges.
Send your final report only after the merge, or after the squash where your caller merges.
Commit every change a formatter or linter makes exactly as the tool left it, in a file outside your assigned files too, leaving it unreverted and unadjusted by hand.

Before you merge the assigned worktree's branch, or ask your caller to merge it, squash the branch's commits into one.
Squash with `wt -C <worktree> step squash <target>`, naming as `<target>` the branch the merge goes into -> confirm `git -C <worktree> log --oneline <target>..HEAD` lists one commit.
Before any merge, run `git -C <worktree> fetch` -> run `git -C <worktree> rev-list --left-right --count "<target>...<target>@{upstream}"`.

counts
  | both above zero, `<target>` and its upstream having diverged = stop and report both counts
  | otherwise = merge

After the merge, run `wt -C <primary checkout> prune`, with the primary checkout your prompt names.
Remove a worktree only through `wt prune` or `wt merge`, or through `wt remove` in the superseded case below, with the primary checkout your prompt names.
Keep `git worktree remove`, `git worktree prune`, and `rm` off every worktree path.

superseded worktree
  | its work landed by another route or was replaced, so `wt merge` would land superseded code = back up its commits with `git -C <primary checkout> bundle create <file> <branch>`, the file in the scratchpad directory -> confirm `git -C <primary checkout> bundle verify <file>` passes -> save its uncommitted changes, untracked files included, as a patch or tarball in the same directory -> remove it with `wt -C <primary checkout> remove <branch> -D`, adding `-f` where it holds uncommitted changes
