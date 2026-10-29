<!-- rule: worktrees -->

## worktrees

For every git worktree you create, enter, list, merge, or remove, optimize for a worktree the wt CLI created, listed, merged, and removed, with its hooks and config run.

- wt: worktrunk, documented at https://worktrunk.dev, its config, hooks included, at `~/.dotfiles/.config/worktrunk/config.toml`

Create with `wt --yes switch --create $branch --base $base`, naming as `$base` the branch the work builds on. List with `wt list`. Remove with `wt remove`. Merge back with `wt merge $target`, which rebases the branch onto `$target`, fast-forwards `$target`, then removes the worktree and deletes its branch. Answer a question about wt from its config file and docs. Keep the EnterWorktree and ExitWorktree tools and the Agent tool's isolation argument out of managing a worktree.

Address files in a worktree by the absolute path wt prints.
A delegate works in its own worktree ? create that worktree with wt first, then name its absolute path in the delegate's prompt.

Before merging, run `git fetch`, then `git rev-list --left-right --count "$target...$target@{upstream}"`.
Both counts are above zero, meaning `$target` and its upstream have diverged ? stop and report both counts : merge.
