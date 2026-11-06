## git-commit

For every commit and commit message, optimize for a commit whose message says what the diff does and why, and whose hooks ran.

### The message

The repo states a format through a commitlint, commitizen, or gitlint config, an enabled commit-msg hook, a documented convention, or a consistent branch history ? follow it exactly : open on one line of the form `$type($scope): $description`, with the type one of feat, fix, docs, style, refactor, perf, test, build, ci, chore, or revert, chosen by what the diff does; the scope optional, reused where the branch or repo already uses one; the description imperative, lowercase at its start, without a trailing period, writing identifiers in their real casing; and a body after one blank line saying why the change happened, for the decisions that were yours to make.
Keep URLs and co-author trailers out of every message.

### The commit

Commit once the work unit's checks pass, with no approval asked -> report what landed.
Keep every push and every post to an external platform on its own approval.
During a multi-step build, commit at each green checkpoint, each delegate committing only its own paths with `git commit -- <paths>`, and end every slice with `git status --short` empty.
Stage generated copies in the same commit as the source they derive from.
Verify the staged set with `git diff --cached --name-only`, with a planning artifact in it only on the user's ask -> compose the message -> commit.
A hook rejects ? make the rejection the next task, fix the cause, and commit anew.
Keep `--no-verify` out of every command.
