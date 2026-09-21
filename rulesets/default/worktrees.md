<!-- rule: worktrees -->

## worktrees

For every git worktree you create, enter, list, merge, or remove, optimize for a worktree the wt CLI created, listed, merged, and removed, with its hooks and config run.

Create with `wt --yes switch --create $branch --base $base`, naming as `$base` the branch the work builds on. List with `wt list`. Remove with `wt remove`. Merge back with `wt merge $target`. The wt CLI is worktrunk, documented at https://worktrunk.dev. Its config, hooks included, lives in `~/.dotfiles/.config/worktrunk/config.toml`. Answer a question about wt from that file and those docs.

Address files in a worktree by the absolute path wt prints. Where a delegate is to work in its own worktree, create that worktree with wt first, then name its absolute path in the delegate's prompt.

Before merging, run `git fetch`, then `git rev-list --left-right --count "$target...$target@{upstream}"`. Where both counts are nonzero, `$target` and its upstream have diverged: stop and report the two counts. Otherwise, merge. `wt merge` rebases the branch onto `$target`, fast-forwards `$target`, then removes the worktree and deletes its branch.

Never manage a worktree through the EnterWorktree or ExitWorktree tools. Never make a worktree through the Agent tool's isolation argument.
