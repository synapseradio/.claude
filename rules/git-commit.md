# Committing

This applies when committing, writing a commit message, or moving between branches.

The first line reads `$type($scope): $description`. The type comes from what the diff does: feat, fix, docs, style, refactor, perf, test, build, ci, chore, or revert. The scope is optional, and reused where the branch or repo already uses one. The description is imperative, starts lowercase, ends without a period, and keeps identifiers in their real casing. After one blank line, the body says why the change happened.

When the repo states a format, through a commitlint, commitizen, or gitlint config, an enabled commit-msg hook, a documented convention, or a consistent branch history, follow it exactly, and set the format above aside. When a hook is disabled or its script is absent, follow the format above. Honor content bans either way, such as no URLs or no co-author trailers.

Hooks stand. Never pass `--no-verify`. Never amend a rejected attempt: fix the cause and commit anew. When a hook rejects the commit, make the rejection the next task.

To commit, verify the staged set with `git diff --cached --name-only`, keeping planning artifacts out unless the user asks for them, compose the message, and commit.

Use the fork-based PR workflow on shared branches. Use separate worktrees for parallel work instead of switching branches in one checkout. When rebasing, resolve conflicts with `-X ours` and autosquash by default.
