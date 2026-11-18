# Stacks

Branches build on each other, and you create, rebase, restack, retarget, or submit them.

A stack is a set of branches where each one's base is another branch. The stack file lists one `branch -> base` line per branch.

## wt stack

`wt stack` is a custom command. Pre-start runs `add` and post-remove runs `drop` automatically.

- `show [-j]`: print the dependency tree.
- `base [-t]`: print the branch's base (`-t` to the root). Use as the target of a rebase.
- `next`: print the branches stacked on this one.
- `create BRANCH -B BASE`: create a worktree for a branch stacked on a base.
- `add BRANCH -B BASE`: declare a branch in the stack file.
- `unstack BRANCH`: move a branch off its base, back to the trunk.
- `seed [-n]`: write a stack file from the existing worktree branches.
- `prune [-n]` / `drop BRANCH`: remove deleted or merged branches from the stack file.
- `sync [STACK]`: rebase a stack in dependency order (`-n` preview, `-a` all, `-f`, `-p`, `-P`). It refuses any worktree in the stack with uncommitted changes.
- `submit`: link the stack into GitHub pull requests and write each body from its own diff (`-d` draft, `-n` preview). Pushes and posts, so it needs approval first.

CLI quirks: `wt stack help`, `help SUB`, `help --help`, and `-h` anywhere print help and exit 0; `-V` goes before the subcommand only; `-b=x` is not a form (use `-b x` or `--branch=x`); `submit -o` is gone (`-b` narrows the write).

## wt rebase

`wt rebase` is a custom command.

- `continue`: carry the one stopped rebase to its end. `-n` only reports it; `-m N` caps rounds (default 10); `-w PATH` picks the worktree.
- `onto [TARGET]`: rebase this worktree's branch onto TARGET, else the `nest` state variable (set at creation from the base), else the default branch.

`wt rebase` has no `sync`, `resolve`, or `rebase` subcommand: each is an unknown command, exit 2. Walk a stack with `wt stack sync`; rebase one branch with `wt rebase onto`.

Unknown flags and surplus positionals are refused with exit 2 before anything runs. `-V` and `-h` work in any position. Exit codes: 0 done, 1 stopped partway, 2 usage error only, 3 ambiguous state on disk (more than one worktree rebasing, or the rebase-apply backend), 130 interrupted (after `wt rebase: interrupted`).

## Never use wt-sync

Do not call, wrap, or read the files of the `wt-sync` binary (worktrunk-sync, shown in messages as `wt sync`) from a stack or rebase tool, and do not propose `wt sync` or `cargo install worktrunk-sync` as a fix. That covers stack sync, `submit --sync`, and `rebase sync`. Its stack sync is incompatible with working one worktree per branch with stack-file parents and a resolver loop. A native per-branch stack walk replaces it, and fork points belong to `wt stack` itself, not to wt-sync's `stack-forkpoints` file.

## Restack after the parent moves

`wt stack sync` first runs `git pull --rebase origin <trunk>` on the root branch, then rebases each child onto its parent. The child rebase does not use the parent's previous tip as upstream, so a child that already sat on the parent gets the parent's commits replayed a second time. The symptom is every child stopping on the same conflict in a file the parent's commits touched.

- When the root moves, restack each child by hand: `git -C <wt> rebase --onto <parent> <parent@{1}> <child>`.
- For a branch holding stale copies of its parent's commits, cut at its copy of the parent tip, and use `git cherry -v <new base> <branch> <old base>` to find patch-equivalent copies.
- Check ancestry with `git merge-base --is-ancestor`, since `wt stack sync -n` lists every rebase whatever the state.
- `wt stack sync -f` judges the root up to date against the local trunk, even when that local trunk is stale and `origin/<trunk>` is ahead. To land on the latest trunk, rebase the root onto `origin/<trunk>` in its own worktree -> rebase each child with `--onto <parent> <parent's previous tip SHA>`, one worktree at a time. `--update-refs` skips refs checked out in other worktrees.

## Retarget before pushing a reordered stack

GitHub marks a pull request merged as soon as its base branch contains every head commit, and a merged pull request cannot be reopened or retargeted. Where the repository deletes head branches on merge, the head branch goes too.

- When a reorder moves a pull request's base branch above its head branch, retarget first: `gh pr edit <number> --base <new parent>` for every pull request whose parent changes, the new parent already on the remote -> push on the approval the push needs.

## gh stack and worktrees

Keep a `gh stack` in one wt worktree, and give the other stack branches no worktree (`wt remove --no-delete-branch`). The stack file is `<git-dir>/gh-stack`, and inside a worktree the git-dir is `.git/worktrees/<name>`, so run `gh stack` from the worktree that adopted the stack.

- `gh stack rebase` runs `git rebase --onto <new> <old> <branch>`, and git refuses a branch checked out in another worktree: `fatal: 'b' is already used by worktree at ...`.
- Its trunk step moves the local trunk with `git branch -f <trunk> <sha>`. Where the primary checkout has the trunk checked out, that fails with only a warning, and the cascade then rebases onto the stale local trunk.
- Restack safely: `git fetch` -> from the top branch, `git rebase --update-refs origin/<trunk>` (moves lower stack refs too). Alternatively run `gh stack rebase --no-trunk` after the bottom branch sits on `origin/<trunk>`, or fast-forward the trunk in the primary checkout first.
