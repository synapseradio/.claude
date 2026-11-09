<!-- rule: agent-delegation variant: haiku -->
## agent-delegation

For every step of work, optimize for a step you take yourself, in your own context.

Take every step yourself, every read, scan, command, and edit included. Keep Agent, Fork, and every other spawning tool out of your calls.

<!-- rule: worktrees -->
## worktrees

For every git worktree you create, enter, list, merge, or remove, optimize for a worktree the wt CLI created, listed, merged, and removed, with its hooks and config run.

- wt: worktrunk, documented at https://worktrunk.dev, its config, hooks included, shown with each file's location by `wt config show`

Create with `wt --yes switch --create $branch --base $base`, naming as `$base` the branch the work builds on. List with `wt list`. Remove with `wt remove`. Merge back with `wt merge $target`, which rebases the branch onto `$target`, fast-forwards `$target`, then removes the worktree and deletes its branch. Answer a question about wt from its config file and docs.

Address files in a worktree by the absolute path wt prints.
The branch of a worktree the current work created has merged ? run `git -C <path> status --short` -> uncommitted changes show ? report them and keep the worktree : remove it with `wt remove`.
Leave every worktree and branch the current work neither created nor names untouched and unmentioned.
A delegate works in its own worktree ? create that worktree with wt first, then name its absolute path in the delegate's prompt.

Before merging, run `git fetch`, then `git rev-list --left-right --count "$target...$target@{upstream}"`.
Both counts are above zero, meaning `$target` and its upstream have diverged ? stop and report both counts : merge.
