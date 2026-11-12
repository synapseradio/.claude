<!-- rule: agent-delegation variant: haiku -->
## agent-delegation

For every step of work, optimize for a step you take yourself, in your own context.

Take every step yourself, every read, scan, command, and edit included. Keep Agent, Fork, and every other spawning tool out of your calls.

<!-- rule: worktrees -->
## worktrees

For every piece of work that changes files in a git repository, every request that lands while such work runs, and every git worktree you create, enter, list, merge, or remove, optimize for work split into lanes that run at once without racing, each landing on the trunk as one commit through a worktree the wt CLI created, merged, and removed, with its hooks and config run.

- wt: worktrunk, documented at <https://worktrunk.dev>, its config, hooks included, shown with each file's location by `wt config show`
- lane: a unit of the work whose changed files no other running lane changes
- trunk: the branch the work builds on, where every lane lands
- primary checkout: the repository's main worktree, the directory holding the `.git` that `git rev-parse --path-format=absolute --git-common-dir` prints
- provision: install what the lane's checks need to run in a fresh worktree, its dependencies for one

List with `wt list`. Remove a worktree only through wt, with `wt prune` or by `wt merge`, and keep `git worktree remove`, `git worktree prune`, and `rm` off every worktree path. Answer a question about wt from its config file and docs.
Address files in a worktree by the absolute path wt prints.
Leave every worktree and branch the current work neither created nor names untouched and unmentioned.
A wt command stops because a project hook awaits approval ? stop the lane -> ask the user to review the hooks with `wt config approvals add`.

### Split

Before work starts, and again whenever a new request lands mid-work, split the work into lanes.
Work would change a file a running lane changes ? add it to that lane where you work the lane yourself or its agent has yet to start : hold it until that lane lands, then give it a lane of its own.

### Create

Give each lane its own worktree, created in the primary checkout with `wt --yes switch --create $branch --base $trunk --no-cd`.
The repository's `.config/wt.toml` holds a pre-start hook ? let it provision the worktree : have the lane provision its worktree before its first commit -> propose once, in your next message, a pre-start hook for `.config/wt.toml` that provisions every new worktree.

### Delegate

Keep for yourself the lane that needs the conversation's context most -> give every other lane, whole, to an agent of its own, spawned in the background without the Agent tool's worktree isolation, in place of acting directly on it, whatever its size, and in place of splitting its steps among other agents -> work your lane while the agents run -> track every lane as a task.
No spawning tool is in hand, or your routing keeps implementation work with you ? work every lane yourself, each in its own worktree, landing each before the next starts.
Name in each lane agent's prompt the worktree's absolute path, its branch, the files it may change, the checks to run before each commit, how to provision the worktree where no pre-start hook does, and steps 3 to 5 under Land, written out.
A lane's agent holds no Bash tool ? leave committing and landing out of its prompt -> commit its lane yourself once it reports.

### Land

The lane's own agent lands the lane once its checks pass, and you land your own lane and every lane whose agent holds no Bash tool, in these steps:

1. Run `skill:simplify` over the lane's changes, unless the lane's agent ran it -> commit what it yields -> run `wt -C <worktree> step squash $trunk` -> confirm `git -C <worktree> log --oneline $trunk..HEAD` lists one commit.
2. Run `git -C <worktree> fetch`, then `git -C <worktree> rev-list --left-right --count "$trunk...$trunk@{upstream}"`. Both counts are above zero, meaning the trunk and its upstream have diverged ? stop and report both counts.
3. Run `wt -C <worktree> merge $trunk`, which rebases the branch onto the trunk, fast-forwards the trunk, then removes the worktree and deletes its branch.
4. The merge stops because the trunk moved or the fast-forward was refused ? run it again, at most twice -> it still stops ? report the lane, its branch, and the last error. The merge stops on a rebase conflict ? resolve it in the worktree on its merits -> continue the rebase -> run the merge again, counting the run among the two.
5. Confirm `git -C <primary checkout> log --oneline $trunk` lists the lane as one commit -> report that commit's SHA and subject -> run `wt -C <primary checkout> prune`.

### Races

A hook step you write or change shares a cache, lock, or output path with a step that may run at the same moment, in its own hook or another lane's ? run the two in sequence, as a pipeline, or give each its own state.

### Finish

After every lane lands, in the primary checkout run the work that needs every lane landed, a cleanup or a deletion across lanes for one -> run each test suite once on the trunk -> report each lane's landed SHA and subject.
A worktree the current work created outlives its branch's merge ? run `git -C <path> status --short` -> uncommitted changes show ? report them and keep the worktree : run `wt -C <primary checkout> prune`.
