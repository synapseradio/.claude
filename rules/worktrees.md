# Working in worktrees

This applies when creating, entering, listing, merging, or removing a git worktree.

We value a worktree the wt CLI created, listed, merged, and removed, so its hooks and config ran. A worktree entered without the wt-switch-create skill leaves the session's working directory at the launch checkout, so files there get addressed by the absolute path wt prints. The worktrunk config, its pre-start hooks included, lives in `~/.dotfiles/.config/worktrunk/`.

```sudolang
Commands {
  create: `wt --yes switch --create $branch`
  list: `wt list`
  remove: `wt remove`
  mergeBack: `wt merge $target`
}

worktree = need => match (need) {
  case the session should work inside the new worktree => invoke worktrunk:wt-switch-create,
    which creates the worktree and switches the session's working directory into it
  case configuring wt, its config, or its hooks, or answering a wt question =>
    invoke worktrunk:worktrunk
  case entered without the wt-switch-create skill => address files in the worktree by
    the absolute path wt prints
}

require manage worktrees through the wt CLI, worktrunk at https://worktrunk.dev, never
  through the EnterWorktree or ExitWorktree tools
```
