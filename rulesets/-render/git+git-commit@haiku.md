<!-- rule: git-commit variant: haiku -->
## git-commit

For every commit and commit message, optimize for a commit whose message says what the diff does and why and whose hooks ran.

### The message

format
  | the repo states one, a consistent branch history included = follow it exactly
  | otherwise = open on one line of the form `$type($scope): $description`, then a body after one blank line saying why the change happened for the decisions that were yours to make

- `$type`: one of `feat` `fix` `docs` `style` `refactor` `perf` `test` `build` `ci` `chore` `revert`, chosen by what the diff does
- `$scope`: optional, reused where the branch or repo already uses one
- `$description`: imperative and lowercase at its start, without a trailing period, with identifiers in their real casing

Keep URLs and co-author trailers out of every message.

### The commit

Commit once the work unit's checks pass, with no approval asked -> report what landed.
Keep every push and every post to an external platform on its own approval.
During a multi-step build, commit at each green checkpoint and end every slice with `git status --short` empty.
Each delegate commits only its own paths with `git commit -- <paths>`.
Stage generated copies in the same commit as the source they derive from.
Verify the staged set with `git diff --cached --name-only`, with a planning artifact in it only on the user's ask -> compose the message -> commit.
Keep `--no-verify` out of every command.

worktree
  | you work in one made for the work = commit with `git -C <worktree> commit -- <paths>` naming the worktree by its absolute path, and leave `git -C <worktree> status --short` empty after each commit

hook
  | it rejects = make the rejection the next task -> fix the cause -> commit anew
