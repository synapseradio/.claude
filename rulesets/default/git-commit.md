<!-- rule: git-commit -->

## git-commit

For every commit, commit message, and move between branches, optimize for a commit whose message says what the diff does and why, and whose hooks ran.

### The message

A message opens on one line of the form `$type($scope): $description`. The type is one of feat, fix, docs, style, refactor, perf, test, build, ci, chore, or revert, chosen by what the diff does. The scope is optional, reused where the branch or repo already uses one. The description is imperative, starts lowercase, drops the trailing period, and writes identifiers in their real casing. The body follows one blank line and says why the change happened, for the decisions that were yours to make.

Where the repo states a format through a commitlint, commitizen, or gitlint config, an enabled commit-msg hook, a documented convention, or a consistent branch history, follow it exactly. Otherwise, use the form above. Either way, honor the standing content bans, keeping URLs, co-author trailers, and every mention of the user out of the message.

### The commit

Verify the staged set with `git diff --cached --name-only`, with a planning artifact in it only on the user's ask. Compose the message, then commit. Where a hook rejects, make the rejection the next task, fix the cause, and commit anew. Keep `--no-verify` out of every command. Keep every amend out of retrying a rejected attempt.

### Branches

Where the repository is public and others push to or review the branch, open the PR from your fork. Split a change into one pull request per team that owns code it touches. Treat a pull request's small size as no ground for folding it into another. Give every line of work its own worktree. When rebasing, autosquash by default, resolving conflicts on their merits.
