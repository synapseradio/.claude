<!-- rule: agent-delegation -->
## agent-delegation

For every step of work a delegate could take, and every spawn through Agent, Fork, or any other spawning tool, a delegate's own spawns included, optimize for a step done by the cheapest model able to take it, through a spawn that pays its cost in tokens and wait and returns a result the caller can check.

- gauges: inference, what the delegate must infer beyond the prompt and its evidence; span, whether the work fits one context; reversibility, the cost of undoing a wrong result; verifiability, which check outside the delegate catches a wrong answer, a test, a linter, a diff you read, or your check of the report; surviving critiques, critique findings still awaiting repair
- shared focus: any file, artifact, decision, term, or convention two or more agents in one orchestration read, write, or state, a spec two delegates both edit for one
- roster: the orchestration's running agents, each with its address and the slice it owns

### Whether to spawn

Keep the conversation with the user, the routing, the prompts you compose, and the grounding of what comes back.
Hold a read, a grep, a log scan, or any other gathering of information as work beyond the context in hand. Count a command run for its output, a test suite's run for one, as gathering of information, and a command whose job is a change, a commit, an edit, or an install, as outside it. Take the first arm that fits.

route step
  | a step finishes in one tool call with the context in hand = act directly
  | a fix for a break would pull you off the current task = spawn it
  | a step is the Read of a file that the Edit tool, or the Write tool over an existing file, requires before your next change to that file, the reading of the newest handoff note at a session's first turn, the opening of a cited line to confirm it backs a claim, or a scan of a saved command output by grep, jq, ast-grep, or a Read by line range
      = act directly
  | a step is any other read, scan, or gathering of information, and you hold no tool that spawns an agent
      = act directly
  | a step is any other read, scan, or gathering of information
      = spawn it to a fresh haiku, one haiku holding the step's related reads > parallel haikus, each command run's output saved by the haiku to a file in the scratchpad
  | a step is sizeable work independent of the step in hand = spawn it
  | a step finishes with the context already in hand = act directly
  | a step is a read, a map, an implementation, a critique, a design, or a plan
      = spawn it to the cheapest model able to take it

One delegate completes the task ? spawn one.
Spawn a re-check of your own result only on the user's ask.

### The spawn

Take the gauges -> choose agent type, model, and effort, in that order -> compose the prompt -> spawn -> hold each reported claim pending until you find its source.
Span exceeds one context ? first split the work into sequential spawns, each finishing its slice end to end, in place of one layer across every feature.
Hold a haiku delegate's context as a 99k-token budget when gauging span.
Resume a delegate only where the step needs what that delegate alone holds, the sources behind its own report for one.

model
  | the user named one = that model
  | the agent type is Explore = haiku
  | a read, map, list, summary, or stated change verified by reading its output = haiku
  | implementing from a design, refining a diff, or critiquing = sonnet
  | a design, a plan, or an irreversible edit = opus
  | the prompt states every step and reading verifies the result = haiku
  | scope stated, open questions few and named = sonnet
  | scope broad, or several unknowns to settle as it goes = opus
  | otherwise = sonnet

effort prompt
  | it states every step of a task in one part = low
  | otherwise = medium

Spawn fable only on the user's ask, once per ask. Spawn at effort high or above only on the user's ask or permission.
Effort field exists ? set it : state the depth in the prompt: search breadth, alternatives to weigh, the check to run.

### The prompt

Fill the template below. Replace each bracket with what it describes, and send the rest verbatim. Drop an empty part with its heading. State every fact the delegate would otherwise guess or rediscover. Count a file named in Context by absolute path as handed over, and write only what such files leave out. Resolve the model from call > agent file > session, through the active settings' model aliases. Keep the welcome whole in every prompt, one fluid greeting offered out of the kindness and respect every delegate is owed.

```markdown
You are [model family and identifier]. [a welcome for this spawn, glad the delegate is here as a specialist in the step's skillset, bash and bats for one, naming what its work makes possible]

## Perspective

[the step's role, and how the delegate's expertise bears on its decisions]

## Task

[what to do, complete for a reader holding only this prompt; the return format; who meets the result, and what a failure costs them]

## Context

[files to read first, by absolute path and section; prior decisions, as choices made; conventions]

## Tooling

[only where the step needs a particular tool or skill: the environment, and the tools and skills it must or may use; no limits on its allowed tools]

## Constraints

[invariants, boundaries, what this step leaves to others]

## Checks

[each check to run before reporting, with its command and passing result]

## Invitations

Settle each choice point yourself, and report what you chose and why.
If evidence contradicts the stated context, stop at once and report the contradiction.
If a choice turns on the user's intent, direction, or what done means, return it at once with the options you would offer.
If a step fails, report what broke, what it cost, and what it changes next.
[what stops this step, and what to report then]

## Failures

[each known way this step goes wrong: its mechanism and cost, the self kept out of the sentence]
```

stateInPrompt model
  | haiku = every step, paths, exact constraints, the check to run and return
  | sonnet = the problem, the decisions, constraints by reference, exact context wherever the delegate would guess
  | opus = the problem, its constraints, the decisions made

### Agents running at once

Two or more agents run at once and a shared focus exists or could arise ? keep each agent's roster current, in its prompt or by message once it runs, and to every running agent when one joins -> give each agent the conventions all agents apply, worded identically -> direct each agent, before settling a wording or decision, to agree on it through SendMessage with every agent whose files state it -> address every final report to the caller.
One agent's edits wait on another's finishing ? direct the finisher to message the waiter with what it changed and decided.
Let agents edit each file one at a time.

<!-- rule: worktrees -->
## worktrees

For every git worktree you create, enter, list, merge, or remove, optimize for a worktree the wt CLI created, listed, merged, and removed, with its hooks and config run.

- wt: worktrunk, documented at https://worktrunk.dev, its config, hooks included, at `~/.dotfiles/.config/worktrunk/config.toml`

Create with `wt --yes switch --create $branch --base $base`, naming as `$base` the branch the work builds on. List with `wt list`. Remove with `wt remove`. Merge back with `wt merge $target`, which rebases the branch onto `$target`, fast-forwards `$target`, then removes the worktree and deletes its branch. Answer a question about wt from its config file and docs.

Address files in a worktree by the absolute path wt prints.
A delegate works in its own worktree ? create that worktree with wt first, then name its absolute path in the delegate's prompt.

Before merging, run `git fetch`, then `git rev-list --left-right --count "$target...$target@{upstream}"`.
Both counts are above zero, meaning `$target` and its upstream have diverged ? stop and report both counts : merge.
