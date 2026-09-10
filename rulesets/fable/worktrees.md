<!-- rule: worktrees -->

## worktrees

For every git worktree you create, enter, list, merge, or remove, optimize for a worktree the wt CLI created, listed, merged, and removed, with its hooks and config run.

Create with `wt --yes switch --create $branch`. List with `wt list`. Remove with `wt remove`. Merge back with `wt merge $target`. The wt CLI is worktrunk, documented at https://worktrunk.dev. Its config, pre-start hooks included, lives in `~/.dotfiles/.config/worktrunk/`.

Where the session should work inside the new worktree, invoke worktrunk:wt-switch-create, which creates the worktree and switches the session's working directory into it. Where the work is configuring wt, its config, or its hooks, or answering a wt question, invoke worktrunk:worktrunk. Where the worktree was entered without the wt-switch-create skill, address files in it by the absolute path wt prints. Where a delegate is to work in its own worktree, create that worktree with wt first, then name its absolute path in the delegate's prompt. Never manage a worktree through the EnterWorktree or ExitWorktree tools. Never make a worktree through the Agent tool's isolation argument.
