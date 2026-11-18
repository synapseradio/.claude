<!-- rule: agent-delegation -->
## agent-delegation

For every step a delegate could take and every spawn through any spawning tool, a delegate's own included, optimize for a step done by the cheapest model able to take it through a spawn that pays its cost in tokens and wait and returns a result the caller can check.

- gauges:
  - inference: what the delegate must infer beyond the prompt and its evidence
  - span: whether the work fits one context
  - reversibility: the cost of undoing a wrong result
  - verifiability: the check outside the delegate that catches a wrong answer
  - surviving critiques: critique findings awaiting repair
- gathering: any read or command run for its output, a test suite's run included, never one that changes state
- shared focus: anything two or more agents in one orchestration read or write or state, a term or a convention included
- roster: the orchestration's running agents, each with its address and the slice it owns
- plan work: a step that carries out an approved plan, its landing and its finish included

### Whether to spawn

Keep the conversation with the user, the routing, the prompts you compose and the grounding of what comes back.
Hold gathering as work beyond the context in hand.

route step
  | no spawning tool is in hand = act directly
  | plan work with you at the session's top level = spawn it once for the whole plan in the background at sonnet and effort medium, its prompt holding the plan file's absolute path -> answer what it hands up -> relay its reports -> leave every file the plan covers to it and its delegates
  | a thinkies skill run other than `thinkies:check-notes` = spawn it at opus and effort high -> relay only its final output
  | any work on a shell file but running it, a git hook or a bats suite included = spawn it with a prompt for the task
  | it finishes in one tool call with the context in hand = act directly
  | git work needing judgment as it goes, such as a rebase with conflicts = spawn it
  | a git operation whose command you can state whole, outside a slice you built = spawn it at haiku
  | an observed failure of unknown cause = spawn it
  | a break's fix would pull you off the current task = spawn it
  | the Read that Edit or an overwriting Write requires before your next change = act directly
  | the newest handoff note read at a session's first turn = act directly
  | a cited line opened to confirm it backs a claim = act directly
  | a scan of saved command output = act directly
  | any other gathering = spawn a fresh haiku, one holding the step's related reads > parallel haikus, each saving every command run's output to a scratchpad file
  | a unit of a plan whose units run in sequence on one working tree = act directly, whatever delegates the plan names, its gathering spawned as above and every verdict on its work judged by you
  | sizeable work independent of the step in hand = spawn it
  | it finishes with the context in hand = act directly
  | a map or an implementation or a critique or a design or a plan = spawn it

Spawn one delegate where one completes the task.
Spawn a re-check of your own result only on the user's ask.

change
  | it edits only comment text, JSDoc included = commit it with no check run and no runner spawned

### The spawn

Take the gauges -> choose the agent type whose description claims the step, then model and effort by the blocks below -> compose the prompt -> spawn -> hold each reported claim pending until you find its source.

span
  | it exceeds one context, a haiku delegate's held as a 99k-token budget = split the work into sequential spawns that each finish a slice end to end, in place of one layer across every feature

model
  | the user named one = that model
  | the step's route line names one = that model
  | a read, a verbatim copy of a prepared payload, or a git operation the prompt states whole = haiku
  | implementing from a design, refining a diff, or critiquing = sonnet
  | a design, a plan, or an irreversible edit = opus
  | the prompt states every step, reading verifies the result, and no file changes = haiku
  | scope stated, open questions few and named = sonnet
  | scope broad, or several unknowns to settle as it goes = opus
  | otherwise = sonnet

Spawn fable only on the user's ask, once per ask.

effort prompt
  | the user asked for or permitted one = that effort
  | a sonnet delegate's prompt states every step in one part = low
  | the delegate runs on sonnet = medium
  | the step's route line names one = that effort
  | it states every step of a task in one part = low
  | otherwise = medium

effort field
  | it exists = set it
  | otherwise = state the depth in the prompt: search breadth, alternatives to weigh, the check to run

### What comes back

Resume a delegate only where the step needs what it alone holds, such as the sources behind its own report.

return
  | review findings = send the delegate that did the work only the user's decisions and defects in the behavior the task requests -> drop every other finding, unmentioned and unasked
  | a question handed up in a message or a report = answer one under the caller's mark from the plan and what you hold -> put one under the standing question to the user through AskUserQuestion -> send the answer through SendMessage at its agent ID, which resumes it where it stopped

### Agents running at once

agents
  | two or more run at once and a shared focus exists or could arise = keep each agent's roster current in its prompt and then by message, telling every running agent when one joins -> give all agents their shared conventions worded identically -> direct each agent to agree each wording or decision through SendMessage with every agent whose files state it before settling it -> address every final report to the caller

wait
  | one agent's edits wait on another's finishing = direct the finisher to message the waiter with what it changed and decided

Let agents edit each file one at a time.

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
