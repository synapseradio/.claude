## toolchain

For every repository's toolchain and lint rules and every dependency you add or change, optimize for code that passes the checks the toolchain runs, on dependencies pinned the way the repository pins them.

### Toolchain

Before the first source file, extend what the repository has into the language's standard toolchain -> write each line to pass it.
Include one version pin every tool reads, a strict type checker, and a commit hook.
Import through the module system, with runtime load-path edits kept out.
Name each module so it imports by name and shadows nothing.
Keep every inline suppression directive out of the code -> restructure until the check passes.

commit hook
  | it skips a formatter, safe autofix, or linter its toolchain offers = add it to run on the staged files with the fixed files restaged

### Dependencies

Treat fewer dependencies as no ground for hand-rolling a job, and a missing module as no ground for a standard-library stand-in or for dropping the task.
Install a Python tool with `uv tool install`.
State the package and version in the message that installs it.
Declare every direct dependency at an exact version or a `~` patch range, `~` by default.
Add a package bare, with its version kept off the command line -> narrow the range the package manager wrote.
Leave override floors on transitive packages as the repository's version convention sets them.
Before changing a pinned version, find what binds it, holding a recorded reason as a lead until a run confirms the coupling -> move every package bound to it in the same change.

dependency
  | a common, maintained library does a job the code needs = install it and use it, in place of a hand-rolled implementation
  | an update, add, or audit fix touches a direct one = narrow every `^` it wrote

### Lint rules

Keep every lint rule enabled.
Read a lint rule's own metadata, its fix classification and severity, before predicting what a fix run changes.
Take a git hook's own edits as they land, with diffing or auditing them kept out.

lint rule
  | it conflicts with a compiler strictness flag = change the types or the interface until both pass, the config unchanged
  | its premise misses a package, such as a React hook rule where no React code runs = disable it in that package's own config alone, with a comment linking the rule's docs
  | unsure whether the premise applies = ask before disabling
