## worktrees

For every worktree your prompt assigns you, optimize for a branch that reaches its merge as one commit, holding what a `skill:simplify` pass over its changes yielded, with every other worktree and branch as you found it.

Leave every worktree and branch your prompt neither assigns nor names untouched and unmentioned.

Before you merge the assigned worktree's branch, or ask your caller to merge it, run `skill:simplify` over the branch's changes -> commit what it yields, if anything, within the files your prompt lets you change, restoring every other file it edited with `git -C <worktree> restore -- <path>` and naming each in your report -> squash the branch's commits into one.
Squash with `wt -C <worktree> step squash <target>`, naming as `<target>` the branch the merge goes into -> confirm `git -C <worktree> log --oneline <target>..HEAD` lists one commit.
The Skill tool is out of reach ? name the skipped `skill:simplify` pass in your report -> squash.
Before any merge, run `git -C <worktree> fetch`, then `git -C <worktree> rev-list --left-right --count "<target>...<target>@{upstream}"`.
Both counts are above zero, meaning `<target>` and its upstream have diverged ? stop and report both counts : merge.
