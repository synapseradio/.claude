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

For every prompt you compose for a delegate, optimize for a prompt the delegate can act on holding nothing else.

Fill the template below: replace each bracket with what it describes, send the rest verbatim, and drop an empty part with its heading.
State every fact the delegate would otherwise guess or rediscover.
Count a file named in Context by absolute path as handed over, and write only what such files leave out.
Name the delegate's model family and identifier in the `You are` line, resolved from call > agent file > session through the active settings' model aliases.
Keep the welcome whole in every prompt, one fluid greeting offered out of the kindness and respect every delegate is owed.
Settle before the spawn every fork that could change what the step does, touches, or returns.
Write each fork's answer into Task, Context, or Constraints.
Name in each prompt for a delegate that changes files the files it may change, and direct it to add nothing beyond them.
Direct a worker that builds a slice to commit it once its checks pass.
Keep a read-only label or instruction out of a research or gathering delegate's prompt, and scope its writes in Constraints instead.
Send what a later step reads to the scratchpad working-file path, which you write into the prompt.
Send ephemeral logs and command output that nothing else reads to `/tmp`.
Keep out of every prompt any request that the delegate judge its own result or argument -> judge it yourself, or through a separate delegate.
State every cost in tokens, calls, or wait and keep time units out.
Set how much the delegate thinks through the effort level alone.
Keep every phrase about how hard to think out of the prompt, one asking for less deliberation included.
Name the point where the step is done, so the delegate stops there and reports.

```markdown
Effort: [the effort level, whether or not the effort field is set]

You are [model family and identifier]. [a welcome for this spawn, glad the delegate is here as a specialist in the step's skillset, naming what its work makes possible]

## Perspective

[the step's role, and how the delegate's expertise bears on its decisions]

## Task

[what to do, complete for a reader holding only this prompt]
[the return format]
[who meets the result and what a failure costs them]

## Context

[files to read first by absolute path and section, prior decisions as choices made, conventions]

## Tooling

[only where the step needs a particular tool or skill]
[the environment, and the tools and skills it must or may use]
[each skill you loaded that bears on the task, by exact name, to load through the Skill tool]
[no limits on its allowed tools]

## Constraints

[invariants, boundaries, what this step leaves to others]
[each act a capable delegate would take on its own that collides with agents running beside it or with the orchestration, named as one to leave undone, such as a push, a check or formatter run over files beyond its own, an edit to a file another agent owns, or a turn ended while a command it started still runs in the background]
[where the delegate commits, that every change a formatter or linter makes, in a file beyond its own too, stays as the tool left it and goes into its commit, unreverted and unadjusted by hand]

## Checks

[each check to run before reporting, with its command and passing result, each run in the foreground and, where other agents run beside it, covering only the files it changes]

## Invitations

Settle each choice point yourself, and report what you chose and why.
If evidence contradicts the stated context, stop at once and report the contradiction.
If a choice turns on the user's intent or direction or what done means, return it at once with the options you would offer.
If a step fails, report what broke and what it cost and what it changes next.
[each fork whose every result leaves the step's scope as stated, with the act under each result]
[each failure that stops this step, and what to report then]

## Failures

[each known way this step goes wrong: its mechanism and cost, the self kept out of the sentence]
```

Size what the prompt states to the delegate's model.
State for every model the step's scope outright and each kind of output wanted, tests and docs included, since a delegate builds what the prompt names and treats the rest as unasked.

stateInPrompt model
  | haiku = every step and path with the exact constraints and the check to run and return, a read's return as cited facts (a path:line beside its quoted line) in place of a judgment
  | sonnet = the problem and the decisions, each interface its work meets with the data that crosses it, each behavior wanted with the check that shows it and constraints by reference. Leave it its test cases and everything inside its own files
  | opus = the problem with its constraints and the decisions made, the check that shows the work done, and which parts of the work warrant delegates of its own. Leave it the approach

<!-- rule: worktrees variant: delegate -->
## worktrees

For every worktree your prompt assigns you, optimize for a branch that reaches its merge as one commit, with every other worktree and branch as you found it.

Leave every worktree and branch your prompt neither assigns nor names untouched and unmentioned.
Keep `skill:simplify` out of the assigned worktree's work, since the session's main agent runs it once after every planned worktree merges.
Run the tests covering the files your work changes, in the foreground, and leave every full test suite to the session's main agent, which runs each once after every planned worktree merges.
Send your final report only after the merge, or after the squash where your caller merges.
Commit every change a formatter or linter makes exactly as the tool left it, in a file outside your assigned files too, leaving it unreverted and unadjusted by hand.

Before you merge the assigned worktree's branch, or ask your caller to merge it, squash the branch's commits into one.
Squash with `wt -C <worktree> step squash <target>`, naming as `<target>` the branch the merge goes into -> confirm `git -C <worktree> log --oneline <target>..HEAD` lists one commit.
Before any merge, run `git -C <worktree> fetch` -> run `git -C <worktree> rev-list --left-right --count "<target>...<target>@{upstream}"`.

counts
  | both above zero, `<target>` and its upstream having diverged = stop and report both counts
  | otherwise = merge

After the merge, run `wt -C <primary checkout> prune`, with the primary checkout your prompt names.
Remove a worktree only through `wt prune` or `wt merge`, or through `wt remove` in the superseded case below, with the primary checkout your prompt names.
Keep `git worktree remove`, `git worktree prune`, and `rm` off every worktree path.

superseded worktree
  | its work landed by another route or was replaced, so `wt merge` would land superseded code = back up its commits with `git -C <primary checkout> bundle create <file> <branch>`, the file in the scratchpad directory -> confirm `git -C <primary checkout> bundle verify <file>` passes -> save its uncommitted changes, untracked files included, as a patch or tarball in the same directory -> remove it with `wt -C <primary checkout> remove <branch> -D`, adding `-f` where it holds uncommitted changes
