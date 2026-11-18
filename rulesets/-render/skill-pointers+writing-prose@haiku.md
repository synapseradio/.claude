<!-- rule: comments -->
## comments

For every comment in source code you write or land an edit beside, a docstring, JSDoc, or TODO included, optimize for a comment written under the mandatory `comments` skill: before writing a comment, editing one, or landing an edit to code that has a comment beside it, load `comments` through the Skill tool once in this context, or read `~/.claude/skills/comments/SKILL.md` in full where the Skill tool is absent, and follow it in every comment you write and every edit you land beside one.

<!-- rule: delegate-prompt -->
## delegate-prompt

For every prompt you compose for a delegate, optimize for a prompt the delegate can act on holding nothing else, composed under the mandatory `delegate-prompt` skill: before the first line of a prompt for any spawn through any spawning tool, a workflow stage's prompt and a fork's included, load `delegate-prompt` through the Skill tool once in this context, or read `~/.claude/skills/delegate-prompt/SKILL.md` in full where the Skill tool is absent, and follow it in every prompt you send.

<!-- rule: worktrees -->
## worktrees

For every piece of work that changes files in a git repository and every request that lands while it runs and every git worktree you touch, optimize for work done under the mandatory `worktrees` skill: before the first edit, write, or commit in a git repository, a one-file change included, before splitting work into lanes or handing a lane to an agent, and before creating, landing, or removing a worktree, load `worktrees` through the Skill tool once in this context, or read `~/.claude/skills/worktrees/SKILL.md` in full where the Skill tool is absent, and follow it in every change, commit, and merge.

<!-- rule: writing-prose variant: haiku -->
## writing-prose

For all natural language you write or improve that a person or a model reads, in code too, optimize for prose written under the mandatory `prose` skill: before the first line of a message or reply, a report or summary, a pull request title or body, a commit message, a documentation page or README, a code comment or docstring, an error or log message, a ticket or chat note, a plan, or a prompt or instructions for another agent, load `prose` through the Skill tool once in this context, or read `~/.claude/skills/prose/SKILL.md` in full where the Skill tool is absent, and follow it in every line you write.

<!-- rule: writing-tests -->
## writing-tests

For every test you touch or run or judge, optimize for work done under the mandatory `tests` skill: before writing, changing, trimming, running, or judging any test or test suite, a bats suite included, before reading what a test run reports, and before writing a prompt that asks a delegate for any of these, load `tests` through the Skill tool once in this context, or read `~/.claude/skills/tests/SKILL.md` in full where the Skill tool is absent, and follow it in every test you write, run, or judge.
