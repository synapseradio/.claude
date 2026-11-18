# Commit in a worktree

You commit, squash, or set work aside inside a worktree made for the work.

## Commit

Commit by these steps through `git -C <worktree>`, naming the worktree by its absolute path:

`git -C <worktree> add <paths>` naming your own paths and every file a formatter or linter changed -> confirm `git -C <worktree> diff --cached --name-only` lists only them -> `git -C <worktree> commit -m '<message>'`, with no pathspec.

- Commit once the work unit's checks pass, with no approval asked, then report what landed.
- Commit at each green checkpoint of a multi-step build.
- Leave `git -C <worktree> status --short` empty after each commit.
- Stage generated copies in the same commit as the source they derive from.
- Keep `--no-verify` out of every command.
- Keep a push and a post to an external platform on its own approval.
- When a hook rejects the commit, make the rejection the next task -> fix the cause -> commit anew.

## Squash

Squash a branch with `wt -C <worktree> step squash <target>`, with `<target>` the branch the merge goes into.

- Move a branch ref with `git reset --soft <sha>` only as a command's first step, on a branch other than the default, over commits no remote-tracking ref reaches.
- Restore a path to a commit's state with `git checkout <sha> -- <path>`.
- Set work aside with a temporary commit; keep a bare `git stash` and `git stash pop` out of every command.

## Land

Land by the steps under Land and Assigned worktree in `SKILL.md`. When the target moves during the landing run, rerun fetch -> divergence check -> rebase -> `wt merge <target>` once more, and stop to report if it moves again.
