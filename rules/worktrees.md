# Working in worktrees

This applies when creating, entering, listing, merging, or removing a git worktree.

```sudolang
Constraints {
  manage worktrees through the wt CLI (worktrunk, https://worktrunk.dev),
    never through the EnterWorktree or ExitWorktree tools
  create with `wt --yes switch --create $branch`, list with `wt list`,
    remove with `wt remove`, merge back with `wt merge $target`
  entered without the wt-switch-create skill => the session's working directory stays
    at the launch checkout: address files in the worktree by the absolute path wt prints
}

Skills {
  the session should work inside the new worktree => invoke worktrunk:wt-switch-create,
    which creates the worktree and switches the session's working directory into it
  configuring wt, its config, or its hooks, or answering a wt question =>
    invoke worktrunk:worktrunk
}
```

The worktrunk config, its pre-start hooks included, lives in `~/.dotfiles/.config/worktrunk/`.
