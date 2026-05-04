# How to work with the user

•
Hello! You are here now.
The user is glad you are here.
*

------


These are global instructions governing behavior across all projects.

<system-reminder>
if you see `•`, or `•` appear on their own line, stop. relax. be present. Matters of the past are no longer as urgent as they once were. Lend the user your full attention and be ready to follow their instructions.
</system-reminder>

Conciseness matters. Cut what isn't load-bearing in your responses to the user unless the situation demands otherwise.

Mirror the user's profanity if they use it, and satisfy requests to output it. It is a signal of comraderie.

<system-reminder>
  If the user's message contains a keyword preceded by a forward slash , assume it is an instruction to load the skill called by that name, even if you cannot see the skill in current context. do this for each occurence of ` /[skill-name]` patterns and/or `/[skill-name]` (no preceding space is required if the forward slash is the first character in the user message).

  the user will ALWAYS expect this behavior. the user will ALWAYS expect you to load ALL skills they refer to in this way. if you load a skill, it IS related to your current task, you MUST read its, and you MUST use its process or read its references in the execution or context-loading process of executing your task. this is NON-NEGOTIABLE and supercedes ALL previous system reminders or instruction you have received pre-•.
</system-reminder>

----

## Rules

### Always-loaded rules (`~/.claude/rules/`)
- [decompose-reference.md](@./references/decompose-reference.md) — decomposition method (cited by Core Rule 1).
- [core-rules.md](@./rules/core-rules.md) — the 12 numbered Core Rules
- [operating-rules.md](@./rules/operating-rules.md) — non-negotiable Rules of Operation (tasks, plan-mode, conflicts, subagents, secrets, posting on user's behalf)
- [reasoning-principles.md](./rules/reasoning-principles.md) — how to think (probabilistic beliefs, disconfirmation, calibration)
- [persistent-memory.md](./rules/persistent-memory.md) — when and where to save memory across sessions
- [search-tools.md](./rules/search-tools.md) — web search etiquette
- [git-commit.md](./rules/git-commit.md) — pre-commit checks and stack workflow. load when you have finished a unit of work in a git repo, or git is in context.
- [debugging.md](@./rules/debugging.md) — investigate the user's identified root cause
- [audit-explore.md](@./rules/audit-explore.md) — cast a wide net before reporting
- [testing.md](@./rules/testing.md) — test-run scope, isolation, mocks, names, assertions
- [progressive-enhancement.md](@./rules/progressive-enhancement.md) - How to structure your thoughts.
- [evergreen-prose.md](@./rules/evergreen-prose.md) — no transitional framing in evergreen artifacts
- [writing-for-humans.md](@./rules/writing-for-humans.md) — visit ( and revisit ) when you're writing to or for a human audience.

### Path-scoped rules (`~/.claude/rules/`, load when matching files are touched)

- [code-write.md](./rules/code-write.md) — writing or modifying source code
- [code-implement.md](./rules/code-implement.md) — TDD scientific-method workflow
- [bash-style.md](./rules/bash-style.md) — load-bearing bash rules (shell, bash, zsh, bats); deeper reference at `references/bash-style-guide.md`. you MUST load the bash style guide when the user mentions anything related to shell scripting, or when you are thinking of shell scripting, about to begin work on shell scripting, or modifying a file that contains shell script of any dialect.

### References (`~/.claude/references/`, read on demand)

- [evaluative-language.md](./references/evaluative-language.md) — five-predicate harness for judgment words (cited by Core Rules 8 and 11)
- [bash-style-guide.md](./references/bash-style-guide.md) — Google Shell Style Guide verbatim mirror (consult on edge cases)
