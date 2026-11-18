<!-- rule: agent-delegation variant: haiku -->
## agent-delegation

For every step of work, optimize for a step you take yourself, in your own context.

Take every step yourself, every read included.
Keep every spawning tool out of your calls.

<!-- rule: delegate-prompt -->
## delegate-prompt

For every prompt you compose for a delegate, optimize for a prompt the delegate can act on holding nothing else, composed under the mandatory `delegate-prompt` skill: before the first line of a prompt for any spawn through any spawning tool, a workflow stage's prompt and a fork's included, load `delegate-prompt` through the Skill tool once in this context, or read `~/.claude/skills/delegate-prompt/SKILL.md` in full where the Skill tool is absent, and follow it in every prompt you send.

<!-- rule: worktrees -->
## worktrees

For every piece of work that changes files in a git repository and every request that lands while it runs and every git worktree you touch, optimize for work done under the mandatory `worktrees` skill: before the first edit, write, or commit in a git repository, a one-file change included, before splitting work into lanes or handing a lane to an agent, and before creating, landing, or removing a worktree, load `worktrees` through the Skill tool once in this context, or read `~/.claude/skills/worktrees/SKILL.md` in full where the Skill tool is absent, and follow it in every change, commit, and merge.
