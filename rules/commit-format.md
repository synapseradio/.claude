# Commit Message Format

Applies whenever you write or rewrite a commit message.

## Default: Conventional Commits

Write the first line as `type(scope): description` (the commitizen convention).

- **type** takes one of: `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `build`, `ci`, `chore`, `revert`. Pick the type by what the change does, judged from its diff, not from the wording of a task.
- **scope** remains optional. When the branch or repo already establishes one (a ticket id, a package name, an area), reuse it for consistency across the branch.
- **description** reads as an imperative, starts lowercase, and takes no trailing period. Keep proper nouns and identifiers in their real casing.

Put any longer explanation in the body, after one blank line. The body explains why and what matters when changing this later.

## The repository wins

When the repository states its own commit format, follow that instead of this default. Treat any of these as the repository stating a format:

- A commit linter or generator config: commitlint, commitizen, `.czrc`, `.cz.*`, `.commitlintrc*`, `gitlint`, or an equivalent.
- An enabled `commit-msg` hook that checks message shape.
- A documented convention in `CONTRIBUTING`, the docs tree, or an `.ai`/rules file.
- A clear, consistent format already in the branch's own history.

Read the format the repository asks for and match it exactly, including its type list, scope rules, and casing. A disabled hook or a referenced-but-absent script does not count as a stated format; fall back to the default above.

Any content bans the repository sets (no company names, no URLs, no co-author trailers, and the like) hold regardless of format.
