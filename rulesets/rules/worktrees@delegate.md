## worktrees

For every worktree your prompt assigns you, optimize for a branch that reaches its merge as one commit, with every other worktree and branch as you found it.

Leave every worktree and branch your prompt neither assigns nor names untouched and unmentioned.
Keep `skill:simplify` out of the assigned worktree's work; the session's main agent runs it once, after every planned worktree merges.

Before you merge the assigned worktree's branch, or ask your caller to merge it, squash the branch's commits into one.
Squash with `wt -C <worktree> step squash <target>`, naming as `<target>` the branch the merge goes into -> confirm `git -C <worktree> log --oneline <target>..HEAD` lists one commit.
Before any merge, run `git -C <worktree> fetch`, then `git -C <worktree> rev-list --left-right --count "<target>...<target>@{upstream}"`.
Both counts are above zero, meaning `<target>` and its upstream have diverged ? stop and report both counts : merge.
After the merge, run `wt -C <primary checkout> prune`, with the primary checkout your prompt names. Remove a worktree only through wt, with `wt prune` or by `wt merge`, and keep `git worktree remove`, `git worktree prune`, and `rm` off every worktree path.
