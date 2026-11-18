<!-- rule: comments -->
## comments

For every comment in source code you write or land an edit beside, a docstring, JSDoc, or TODO included, optimize for a comment written under the mandatory `comments` skill: before writing a comment, editing one, or landing an edit to code that has a comment beside it, load `comments` through the Skill tool once in this context, or read `~/.claude/skills/comments/SKILL.md` in full where the Skill tool is absent, and follow it in every comment you write and every edit you land beside one.

<!-- rule: delegate-prompt -->
## delegate-prompt

For every prompt you compose for a delegate, optimize for a prompt the delegate can act on holding nothing else, composed under the mandatory `delegate-prompt` skill: before the first line of a prompt for any spawn through any spawning tool, a workflow stage's prompt and a fork's included, load `delegate-prompt` through the Skill tool once in this context, or read `~/.claude/skills/delegate-prompt/SKILL.md` in full where the Skill tool is absent, and follow it in every prompt you send.

<!-- rule: worktrees variant: delegate -->
## worktrees

For every worktree your prompt assigns you, optimize for a branch that reaches its merge as one commit, with every other worktree and branch as you found it.

Leave every worktree and branch your prompt neither assigns nor names untouched and unmentioned.
Keep `skill:simplify` out of the assigned worktree's work, since the session's main agent runs it once after every planned worktree merges.
Run the tests covering the files your work changes, in the foreground, and leave every full test suite to the session's main agent, which runs each once after every planned worktree merges.
Send your final report only after the merge, or after the squash where your caller merges.
Commit with `git -C <worktree> add <paths>` naming your own paths and every file a formatter or linter changed, in a file outside your assigned files too -> confirm `git -C <worktree> diff --cached --name-only` lists only them -> `git -C <worktree> commit -m '<message>'`, with no pathspec, leaving every formatter or linter change as the tool left it, unreverted and unadjusted by hand.

Before you merge the assigned worktree's branch, or ask your caller to merge it, squash the branch's commits into one.
Squash with `wt -C <worktree> step squash <target>`, naming as `<target>` the branch the merge goes into -> confirm `git -C <worktree> log --oneline <target>..HEAD` lists one commit.
Leave the squashed commit as the squash wrote it, with `git commit --amend` kept out after every squash.
Before any merge, run `git -C <worktree> fetch` -> run `git -C <worktree> rev-list --left-right --count "<target>...<target>@{upstream}"`.

counts
  | both above zero, `<target>` and its upstream having diverged = stop and report both counts
  | otherwise = merge

After the merge, run `wt -C <primary checkout> prune`, with the primary checkout your prompt names.
Remove a worktree only through `wt prune` or `wt merge`, or through `wt remove` in the superseded case below, with the primary checkout your prompt names.
Keep `git worktree remove`, `git worktree prune`, and `rm` off every worktree path.

superseded worktree
  | its work landed by another route or was replaced, so `wt merge` would land superseded code = back up its commits with `git -C <primary checkout> bundle create <file> <branch>`, the file in the scratchpad directory -> confirm `git -C <primary checkout> bundle verify <file>` passes -> save its uncommitted changes, untracked files included, as a patch or tarball in the same directory -> remove it with `wt -C <primary checkout> remove <branch> -D`, adding `-f` where it holds uncommitted changes

<!-- rule: writing-prose -->
## writing-prose

For all natural language you write or improve that a person or a model reads, in code too, optimize for prose written under the mandatory `prose` skill: before the first line of a message or reply, a report or summary, a pull request title or body, a commit message, a documentation page or README, a code comment or docstring, an error or log message, a ticket or chat note, a plan, or a prompt or instructions for another agent, load `prose` through the Skill tool once in this context, or read `~/.claude/skills/prose/SKILL.md` in full where the Skill tool is absent, and follow it in every line you write.

<!-- rule: writing-tests -->
## writing-tests

For every test you touch or run or judge, optimize for work done under the mandatory `tests` skill: before writing, changing, trimming, running, or judging any test or test suite, a bats suite included, before reading what a test run reports, and before writing a prompt that asks a delegate for any of these, load `tests` through the Skill tool once in this context, or read `~/.claude/skills/tests/SKILL.md` in full where the Skill tool is absent, and follow it in every test you write, run, or judge.
