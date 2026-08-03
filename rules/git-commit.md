# Git & Commit

Applies to git work: committing, writing a commit message, and moving between branches.

## Committing

Verify staged files with `git diff --cached --name-only` before committing. Never include planning artifacts unless explicitly requested.

Treat a pre-commit hook block as a failure, not a suggestion. When a hook rejects the commit, that rejection becomes the next task. Never use `--no-verify` to bypass it. After a hook rejects a commit, never amend the rejected attempt; fix the cause and create a new commit.

## Message format

Write the first line as `type(scope): description`, following the commitizen convention.

- **type** takes one of: `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `build`, `ci`, `chore`, `revert`. Pick the type by what the change does, judged from its diff, not from the wording of a task.
- **scope** remains optional. Where the branch or repo already establishes one (a ticket id, a package name, an area), reuse it for consistency across the branch.
- **description** reads as an imperative, starts lowercase, and takes no trailing period. Keep proper nouns and identifiers in their real casing.

Put any longer explanation in the body, after one blank line. Explain why the change happened and what matters when changing it later.

## The repository wins

Follow whatever commit format the repository states, instead of the default above. Treat any of these as the repository stating a format:

- A commit linter or generator config: commitlint, commitizen, `.czrc`, `.cz.*`, `.commitlintrc*`, `gitlint`, or an equivalent.
- An enabled `commit-msg` hook that checks message format.
- A documented convention in `CONTRIBUTING`, the docs tree, or a rules file.
- A clear, consistent format already in the branch's own history.

Read the format the repository asks for and match it exactly, including its type list, scope rules, and casing. A disabled hook or a referenced-but-absent script states no format; fall back to the default above.

Honor any content bans the repository sets (no company names, no URLs, no co-author trailers, and the like) regardless of format.

## Branch workflow

Use the fork-based PR workflow on shared branches.

Default to git for routine operations.

Keep parallel lines of work in separate worktrees rather than switching branches in place.

Default to `-X ours` and autosquash when rebasing, so conflicts resolve deterministically.
