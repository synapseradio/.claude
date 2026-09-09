<rule name="git-commit">

## git-commit

When you are committing, writing a commit message, or moving between branches, optimize for a commit whose message says what the diff does and why, and whose hooks ran.

A commit outlives the session that made it, so its message is what a later reader has of the reasons. A hook skipped with `--no-verify` leaves history the repo's own checks never accepted. A rejected attempt amended hides the cause under a fresh attempt. A planning artifact in the staged set reaches history without anyone deciding it should.

### The message

A message opens on one line of the form `$type($scope): $description`. The type is one of feat, fix, docs, style, refactor, perf, test, build, ci, chore, or revert, chosen from what the diff does. The scope is optional, reused where the branch or repo already uses one. The description is imperative, starts lowercase, carries no trailing period, and writes identifiers in their real casing. The body follows one blank line and says why the change happened, for the decisions that were yours to make.

Where the repo states a format through a commitlint, commitizen, or gitlint config, an enabled commit-msg hook, a documented convention, or a consistent branch history, follow it exactly. Otherwise, use the message form above. Honor the standing content bans either way, no URLs and no co-author trailers.

### The commit

Verify the staged set with `git diff --cached --name-only`, with planning artifacts out unless the user asks. Compose the message, then commit. Where a hook rejects, make the rejection the next task, fix the cause, and commit anew. Never pass `--no-verify`. Never amend a rejected attempt.

### Branches

Where the branch is one other people push to or review, open the PR from your fork. Give every line of work its own worktree. When rebasing, autosquash by default, with conflicts resolved on their merits.

</rule>
