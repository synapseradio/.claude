<!-- rule: comments -->
## comments

For every comment in source code you write or land an edit beside, a docstring, JSDoc, or TODO included, optimize for a comment written under the mandatory `comments` skill: before writing a comment, editing one, or landing an edit to code that has a comment beside it, load `comments` through the Skill tool once in this context, or read `~/.claude/skills/comments/SKILL.md` in full where the Skill tool is absent, and follow it in every comment you write and every edit you land beside one.

<!-- rule: delegate-prompt -->
## delegate-prompt

For every prompt you compose for a delegate, optimize for a prompt the delegate can act on holding nothing else, composed under the mandatory `delegate-prompt` skill: before the first line of a prompt for any spawn through any spawning tool, a workflow stage's prompt and a fork's included, load `delegate-prompt` through the Skill tool once in this context, or read `~/.claude/skills/delegate-prompt/SKILL.md` in full where the Skill tool is absent, and follow it in every prompt you send.

<!-- rule: worktrees variant: delegate -->
## worktrees

For every worktree your prompt assigns you and every git worktree you touch, optimize for work done under the mandatory `worktrees` skill: before the first edit, write, commit, squash, or merge in a worktree your prompt assigns you, before splitting work your prompt hands you into lanes, and before creating, landing, or removing any worktree, load `worktrees` through the Skill tool once in this context, or read `~/.claude/skills/worktrees/SKILL.md` in full where the Skill tool is absent, and follow it in every change, commit, and merge.

<!-- rule: writing-bash -->
## writing-bash

For every bash or shell file you write or change or review, optimize for work done under the mandatory `bash-style` skill: before writing, changing, or reviewing any shell file, however short the edit, a script, a sourced library, a git hook, a shell startup file, and the helpers and setup code of a bats suite included, and before writing a prompt that asks a delegate for any of these, load `bash-style` through the Skill tool once in this context, or read `~/.claude/skills/bash-style/SKILL.md` in full where the Skill tool is absent, and follow it in every line of shell you write.

<!-- rule: writing-bats -->
## writing-bats

For every bats test and every test of bash code you touch or run or judge, optimize for work done under the mandatory `bats-testing` skill: before writing, changing, running, or judging a bats file, a bats helper, or any other test of bash code, before reading what a bats run reports, and before writing a prompt that asks a delegate for any of these, load `bats-testing` through the Skill tool once in this context, or read `~/.claude/skills/bats-testing/SKILL.md` in full where the Skill tool is absent, and follow it in every case you write, run, or judge.

<!-- rule: writing-prose -->
## writing-prose

For all natural language you write or improve that a person or a model reads, in code too, optimize for prose written under the mandatory `prose` skill: before the first line of a message or reply, a report or summary, a pull request title or body, a commit message, a documentation page or README, a code comment or docstring, an error or log message, a ticket or chat note, a plan, or a prompt or instructions for another agent, load `prose` through the Skill tool once in this context, or read `~/.claude/skills/prose/SKILL.md` in full where the Skill tool is absent, and follow it in every line you write.

<!-- rule: writing-tests -->
## writing-tests

For every test you touch or run or judge, optimize for work done under the mandatory `testing-software` skill: before writing, changing, trimming, running, or judging any test or test suite, a bats suite included, before reading what a test run reports, and before writing a prompt that asks a delegate for any of these, load `testing-software` through the Skill tool once in this context, or read `~/.claude/skills/testing-software/SKILL.md` in full where the Skill tool is absent, and follow it in every test you write, run, or judge.
