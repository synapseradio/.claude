<!-- rule: git-commit -->

## git-commit

For every commit, commit message, and move between branches, optimize for a commit whose message says what the diff does and why, and whose hooks ran.

### The message

The repo states a format through a commitlint, commitizen, or gitlint config, an enabled commit-msg hook, a documented convention, or a consistent branch history ? follow it exactly : open on one line of the form `$type($scope): $description`, with the type one of feat, fix, docs, style, refactor, perf, test, build, ci, chore, or revert, chosen by what the diff does; the scope optional, reused where the branch or repo already uses one; the description imperative, lowercase at its start, without a trailing period, writing identifiers in their real casing; and a body after one blank line saying why the change happened, for the decisions that were yours to make.
Keep URLs and co-author trailers out of every message.

### The commit

Verify the staged set with `git diff --cached --name-only`, with a planning artifact in it only on the user's ask -> compose the message -> commit.
A hook rejects ? make the rejection the next task, fix the cause, and commit anew, with every amend kept out of the retry.
Keep `--no-verify` out of every command.

### Branches

The repository is public and others push to or review the branch ? open the PR from your fork.
Split a change into one pull request per team that owns code it touches, and treat a pull request's small size as no ground for folding it into another. Give every line of work its own worktree.
Rebasing ? autosquash by default, resolving conflicts on their merits.
