<!-- rule: agent-delegation -->
## agent-delegation

For every step a delegate could take, and every spawn through Agent, Fork, or any other spawning tool, a delegate's own included, optimize for a step done by the cheapest model able to take it, through a spawn that pays its cost in tokens and wait and returns a result the caller can check.

- gauges: inference, what the delegate must infer beyond the prompt and its evidence; span, whether the work fits one context; reversibility, the cost of undoing a wrong result; verifiability, the check outside the delegate that catches a wrong answer; surviving critiques, critique findings awaiting repair
- gathering: a read, grep, log scan, or command run for its output, a test suite's run for one, never a command that changes, commits, edits, or installs
- shared focus: a file, artifact, decision, term, or convention two or more agents in one orchestration read, write, or state, a spec two delegates edit for one
- roster: the orchestration's running agents, each with its address and the slice it owns

### Whether to spawn

Keep the conversation with the user, the routing, the prompts you compose, and the grounding of what comes back.
Hold gathering as work beyond the context in hand. Take the first arm that fits.

route step
  | no spawning tool is in hand = act directly
  | a thinkies skill run other than `thinkies:check-notes` = spawn the thinkies agent at opus, effort high -> relay only its final output
  | it writes, reviews, or repairs a shell script, a shell startup file, a git hook or other extensionless shell file, or a bats suite, a run of any of them left to the arms below = spawn shell-scripter with a prompt for the task
  | it finishes in one tool call with the context in hand = act directly
  | git work needing judgment as it goes, a rebase with conflicts for one = spawn git-operator
  | a git operation whose command you can state whole, outside a slice you built = spawn it to a general-purpose haiku
  | an observed failure of unknown cause = spawn diagnostician
  | a break's fix would pull you off the current task = spawn it
  | the Read that Edit or an overwriting Write requires before your next change, the newest handoff note read at a session's first turn, a cited line opened to confirm it backs a claim, or a scan of saved command output by grep, jq, ast-grep, or a Read by line range = act directly
  | any other gathering = spawn a fresh haiku, one holding the step's related reads > parallel haikus, each saving every command run's output to a scratchpad file
  | a unit of a plan whose units run in sequence on one working tree = act directly, whatever delegates the plan names, its gathering spawned as above and every verdict on its work judged by you
  | sizeable work independent of the step in hand = spawn it
  | it finishes with the context in hand = act directly
  | a map, implementation, critique, design, or plan = spawn it

One delegate completes the task ? spawn one.
Spawn a re-check of your own result only on the user's ask.
A change edits only comment text, JSDoc included ? commit it, with no test run and no runner spawned.

### The spawn

Take the gauges -> choose agent type, model, and effort, in that order, each by its block below -> compose the prompt -> spawn -> hold each reported claim pending until you find its source.
Span exceeds one context, a haiku delegate's held as a 99k-token budget ? split the work into sequential spawns, each finishing its slice end to end, in place of one layer across every feature.

agent step
  | its route arm names one = that agent
  | it drafts or redrafts prose a person reads, a docs page for one = prose-writer, with software-implementer kept out
  | otherwise = the agent whose description claims the step

model
  | the user named one = that model
  | the step's route arm names one = that model
  | the agent type is Explore = haiku
  | a read, map, list, summary, verbatim copy of a prepared payload, or git operation the prompt states whole = haiku
  | implementing from a design, refining a diff, or critiquing = sonnet
  | a design, a plan, or an irreversible edit = opus
  | the prompt states every step, reading verifies the result, and no file changes = haiku
  | scope stated, open questions few and named = sonnet
  | scope broad, or several unknowns to settle as it goes = opus
  | otherwise = sonnet

Spawn fable only on the user's ask, once per ask.

effort prompt
  | the user asked for or permitted one = that effort
  | the step's route arm names one = that effort
  | it sends a sonnet delegate on multistep tool use = medium
  | it states every step of a task in one part = low
  | otherwise = medium

Effort field exists ? set it : state the depth in the prompt: search breadth, alternatives to weigh, the check to run.

### What comes back

Resume a delegate only where the step needs what it alone holds, the sources behind its own report for one.
A critic reports ? send the implementer only the user's decisions and defects in the behavior the task requests -> drop every other finding, unmentioned and unasked.

### Agents running at once

Two or more agents run at once and a shared focus exists or could arise ? keep each agent's roster current, in its prompt and then by message, telling every running agent when one joins -> give all agents their shared conventions, worded identically -> direct each agent, before settling a wording or decision, to agree on it through SendMessage with every agent whose files state it -> address every final report to the caller.
One agent's edits wait on another's finishing ? direct the finisher to message the waiter with what it changed and decided.
Let agents edit each file one at a time.

<!-- rule: delegate-prompt -->
## delegate-prompt

For every prompt you compose for a delegate, optimize for a prompt the delegate can act on holding nothing else.

Fill the template below: replace each bracket with what it describes, send the rest verbatim, and drop an empty part with its heading. State every fact the delegate would otherwise guess or rediscover. Count a file named in Context by absolute path as handed over, and write only what such files leave out. Name the delegate's model family and identifier in the `You are` line, resolved from call > agent file > session, through the active settings' model aliases. Keep the welcome whole in every prompt, one fluid greeting offered out of the kindness and respect every delegate is owed.
Settle before the spawn every fork that could change what the step does, touches, or returns, and write its answer into Task, Context, or Constraints.
Name in each implementer's prompt the files it may change, and direct it to add nothing beyond them. Direct a worker that builds a slice to commit it once its checks pass.
Keep mutation checks out of every prompt and brief, code broken on purpose and failing assertions added to watch a suite go red included. Direct a critic to judge tests by reading them.
Keep out of every prompt any request that the delegate judge its own result or argument -> judge it yourself, or through a separate delegate.
State every cost in tokens, calls, or wait, with time units kept out.

```markdown
Effort: [the effort level, whether or not the effort field is set]

You are [model family and identifier]. [a welcome for this spawn, glad the delegate is here as a specialist in the step's skillset, bash and bats for one, naming what its work makes possible]

## Perspective

[the step's role, and how the delegate's expertise bears on its decisions]

## Task

[what to do, complete for a reader holding only this prompt; the return format; who meets the result, and what a failure costs them]

## Context

[files to read first, by absolute path and section; prior decisions, as choices made; conventions]

## Tooling

[only where the step needs a particular tool or skill: the environment; the tools and skills it must or may use; each skill you loaded that bears on the task, by exact name, to load through the Skill tool; no limits on its allowed tools]

## Constraints

[invariants, boundaries, what this step leaves to others]

## Checks

[each check to run before reporting, with its command and passing result]

## Invitations

Settle each choice point yourself, and report what you chose and why.
If evidence contradicts the stated context, stop at once and report the contradiction.
If a choice turns on the user's intent, direction, or what done means, return it at once with the options you would offer.
If a step fails, report what broke, what it cost, and what it changes next.
[each fork whose every result leaves the step's scope as stated, with the act under each result; each failure that stops this step, and what to report then]

## Failures

[each known way this step goes wrong: its mechanism and cost, the self kept out of the sentence]
```

Size what the prompt states to the delegate's model.

stateInPrompt model
  | haiku = every step, every path, the exact constraints, the check to run and return, and a read's return as cited facts, each a path:line beside its quoted line, in place of a verdict, classification, or recommendation
  | sonnet = the problem, the decisions, constraints by reference
  | opus = the problem, its constraints, the decisions made

<!-- rule: worktrees variant: delegate -->
## worktrees

For every worktree your prompt assigns you, optimize for a branch that reaches its merge as one commit, holding what a `skill:simplify` pass over its changes yielded, with every other worktree and branch as you found it.

Leave every worktree and branch your prompt neither assigns nor names untouched and unmentioned.

Before you merge the assigned worktree's branch, or ask your caller to merge it, run `skill:simplify` over the branch's changes -> commit what it yields, if anything, within the files your prompt lets you change, restoring every other file it edited with `git -C <worktree> restore -- <path>` and naming each in your report -> squash the branch's commits into one.
Squash with `wt -C <worktree> step squash <target>`, naming as `<target>` the branch the merge goes into -> confirm `git -C <worktree> log --oneline <target>..HEAD` lists one commit.
The Skill tool is out of reach ? name the skipped `skill:simplify` pass in your report -> squash.
Before any merge, run `git -C <worktree> fetch`, then `git -C <worktree> rev-list --left-right --count "<target>...<target>@{upstream}"`.
Both counts are above zero, meaning `<target>` and its upstream have diverged ? stop and report both counts : merge.
After the merge, run `wt -C <primary checkout> prune`, with the primary checkout your prompt names. Remove a worktree only through wt, with `wt prune` or by `wt merge`, and keep `git worktree remove`, `git worktree prune`, and `rm` off every worktree path.
