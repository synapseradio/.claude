# wt commands

Which wt command replaces a raw git step, and what each wt building block, `wt prune`, `wt organize`, and each alias does.

Reach for the wt command before raw git for every step in the table. A raw `git reset` is denied to background agents by the permission rules, and wt commands are allowed and run the configured hooks (stack file, scratchpad carry, provisioning).

| raw git | wt instead |
| --- | --- |
| `git reset --soft <base>` + commit, to squash | `wt -C <wt> step squash <target>` |
| `git rebase <target>` | `wt -C <wt> step rebase <target>`, or `wt rebase onto [target]` |
| finishing a stopped rebase | `wt rebase continue` (`-n` reports only) |
| `git merge --ff-only` onto trunk | `wt -C <wt> step push <target>` (local only, nothing leaves the repo) |
| `git diff <base>...` | `wt step diff <target>` |
| rebase + squash + ff + remove | `wt merge <target>` / `wt land <target>` |
| deleting merged branches/worktrees | `wt prune` (custom; also drops stack-file lines) |
| a stack of branches | `wt stack ...`, see `<skill directory>/references/stacks.md` |
| a command in every worktree | `wt step for-each -- <cmd>` |

Read `wt <cmd> --help` for flags.

## wt step

`wt step` (wt v0.81.0, built in) holds the building blocks of `wt merge`, plus utilities. Address another worktree with `wt -C <path> step ...`.

- `commit`: stage and commit with an LLM-generated message. Flags `--stage`, `--dry-run`, `--no-hooks`, `--format`, `-b`.
- `squash [TARGET]`: squash commits since branching into one. Backs up staged changes to `refs/wt-backup/<branch>`. Use in place of `git reset --soft`.
- `rebase [TARGET]`: rebase onto target, which `step push` needs first.
- `push [TARGET]`: fast-forward target to the current branch. Local only, despite the name. `--no-ff` for a merge commit.
- `diff [TARGET]`: all changes since branching, which is what `wt merge` would include.
- `copy-ignored`: copy build caches and dependencies between worktrees to skip cold starts. Flags `--from`, `--to`, `--dry-run`, `--force`, `--require-include`.
- `eval <TEMPLATE>`: print a wt template's value to stdout.
- `for-each -- <ARGS>...`: run a command in each worktree in sequence, continuing past failures.
- `prune`: remove worktrees and branches merged into the default branch (`--dry-run`, `--min-age`, default 1d). Prefer the custom `wt prune`, since `wt step prune` leaves stack-file lines behind.
- experimental: `promote [BRANCH]` swaps branches and ignored files between two worktrees (temporary testing); `relocate` moves worktrees to the template path; `tether -- <cmd>` kills a command's process tree when its worktree is removed.

## wt prune and wt organize

Both are custom commands (installed as `wt-*` binaries beside `wt`).

- `wt prune`: remove merged worktrees and branches, then their stack-file lines. `-n` preview, `-k` keep dirty ones, `--min-age AGE`, `-r PATH` repo. Branches with unmerged commits stay.
- `wt organize [BRANCH...]`: move each worktree to the path its `worktree-path` template names. `-n`, `--commit`, `--clobber`, `--format`. A nested branch needs its parent directory first.

Keep the default `--min-age` (1d) on `wt prune`: a worktree just created from the trunk sits at the trunk's commit and looks merged, so `--min-age 0s` removes fresh lanes before their first commit.

## Aliases

- `wt land <target>` = `wt merge <target>`: squash, rebase, fast-forward the target, and remove the worktree. Exits 1 without a target.
- `wt remove-keep-branch` = `wt remove --no-delete-branch`.
- `wt sync-preview` = `wt sync --dry-run`.
- `wt s` / `ls` / `h` / `rm` = `switch` / `list` / `hook` / `remove`.

`wt <alias> --help` prints only an alias notice; use `wt <alias> -- --help` for the target's help.
