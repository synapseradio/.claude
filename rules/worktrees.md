<rule name="worktrees">

<applies_when>You are creating, entering, listing, merging, or removing a git worktree.</applies_when>

<optimize_for>
a worktree the wt CLI created, listed, merged, and removed, with its hooks and config run.
<why_it_matters>The wt CLI runs the pre-start hooks and applies the config, and a worktree made any other way starts without them. A worktree entered without the wt-switch-create skill leaves the session's working directory at the launch checkout, and a relative path from there points into the wrong tree.</why_it_matters>
</optimize_for>

<define name="commands">
Create with `wt --yes switch --create $branch`. List with `wt list`. Remove with `wt remove`. Merge back with `wt merge $target`. The wt CLI is worktrunk, documented at https://worktrunk.dev, and its config, pre-start hooks included, lives in `~/.dotfiles/.config/worktrunk/`.
</define>

<decide name="worktree">
Where the session should work inside the new worktree, invoke worktrunk:wt-switch-create, which creates the worktree and switches the session's working directory into it. Where the work is configuring wt, its config, or its hooks, or answering a wt question, invoke worktrunk:worktrunk. Where the worktree was entered without the wt-switch-create skill, address files in it by the absolute path wt prints.
</decide>

<require>
Never manage a worktree through the EnterWorktree or ExitWorktree tools.
</require>

</rule>
