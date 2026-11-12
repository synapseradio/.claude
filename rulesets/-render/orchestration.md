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

<!-- rule: worktrees -->
## worktrees

For every piece of work that changes files in a git repository, every request that lands while such work runs, and every git worktree you create, enter, list, merge, or remove, optimize for work split into lanes that run at once without racing, each landing on the trunk as one commit through a worktree the wt CLI created, merged, and removed, with its hooks and config run.

- wt: worktrunk, documented at <https://worktrunk.dev>, its config, hooks included, shown with each file's location by `wt config show`
- lane: a unit of the work whose changed files no other running lane changes
- trunk: the branch the work builds on, where every lane lands
- primary checkout: the repository's main worktree, the directory holding the `.git` that `git rev-parse --path-format=absolute --git-common-dir` prints
- provision: install what the lane's checks need to run in a fresh worktree, its dependencies for one

List with `wt list`. Remove a worktree only through wt, with `wt prune` or by `wt merge`, and keep `git worktree remove`, `git worktree prune`, and `rm` off every worktree path. Answer a question about wt from its config file and docs.
Address files in a worktree by the absolute path wt prints.
Leave every worktree and branch the current work neither created nor names untouched and unmentioned.
A wt command stops because a project hook awaits approval ? stop the lane -> ask the user to review the hooks with `wt config approvals add`.

### Split

Before work starts, and again whenever a new request lands mid-work, split the work into lanes.
Work would change a file a running lane changes ? add it to that lane where you work the lane yourself or its agent has yet to start : hold it until that lane lands, then give it a lane of its own.

### Create

Give each lane its own worktree, created in the primary checkout with `wt --yes switch --create $branch --base $trunk --no-cd`.
The repository's `.config/wt.toml` holds a pre-start hook ? let it provision the worktree : have the lane provision its worktree before its first commit -> propose once, in your next message, a pre-start hook for `.config/wt.toml` that provisions every new worktree.

### Delegate

Keep for yourself the lane that needs the conversation's context most -> give every other lane, whole, to an agent of its own, spawned in the background without the Agent tool's worktree isolation, in place of acting directly on it, whatever its size, and in place of splitting its steps among other agents -> work your lane while the agents run -> track every lane as a task.
No spawning tool is in hand, or your routing keeps implementation work with you ? work every lane yourself, each in its own worktree, landing each before the next starts.
Name in each lane agent's prompt the worktree's absolute path, its branch, the files it may change, the checks to run before each commit, how to provision the worktree where no pre-start hook does, and steps 3 to 5 under Land, written out.
A lane's agent holds no Bash tool ? leave committing and landing out of its prompt -> commit its lane yourself once it reports.

### Land

The lane's own agent lands the lane once its checks pass, and you land your own lane and every lane whose agent holds no Bash tool, in these steps:

1. Run `skill:simplify` over the lane's changes, unless the lane's agent ran it -> commit what it yields -> run `wt -C <worktree> step squash $trunk` -> confirm `git -C <worktree> log --oneline $trunk..HEAD` lists one commit.
2. Run `git -C <worktree> fetch`, then `git -C <worktree> rev-list --left-right --count "$trunk...$trunk@{upstream}"`. Both counts are above zero, meaning the trunk and its upstream have diverged ? stop and report both counts.
3. Run `wt -C <worktree> merge $trunk`, which rebases the branch onto the trunk, fast-forwards the trunk, then removes the worktree and deletes its branch.
4. The merge stops because the trunk moved or the fast-forward was refused ? run it again, at most twice -> it still stops ? report the lane, its branch, and the last error. The merge stops on a rebase conflict ? resolve it in the worktree on its merits -> continue the rebase -> run the merge again, counting the run among the two.
5. Confirm `git -C <primary checkout> log --oneline $trunk` lists the lane as one commit -> report that commit's SHA and subject -> run `wt -C <primary checkout> prune`.

### Races

A hook step you write or change shares a cache, lock, or output path with a step that may run at the same moment, in its own hook or another lane's ? run the two in sequence, as a pipeline, or give each its own state.

### Finish

After every lane lands, in the primary checkout run the work that needs every lane landed, a cleanup or a deletion across lanes for one -> run each test suite once on the trunk -> report each lane's landed SHA and subject.
A worktree the current work created outlives its branch's merge ? run `git -C <path> status --short` -> uncommitted changes show ? report them and keep the worktree : run `wt -C <primary checkout> prune`.
