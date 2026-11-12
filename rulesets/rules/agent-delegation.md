## agent-delegation

For every step a delegate could take, and every spawn through Agent, Fork, or any other spawning tool, a delegate's own spawns included, optimize for a step done by the cheapest model able to take it, through a spawn that pays its cost in tokens and wait and returns a result the caller can check.

- gauges: inference, what the delegate must infer beyond the prompt and its evidence; span, whether the work fits one context; reversibility, the cost of undoing a wrong result; verifiability, which check outside the delegate, a test or your own read of its result, catches a wrong answer; surviving critiques, critique findings awaiting repair
- gathering: a read, a grep, a log scan, or a command run for its output, a test suite's run for one, with every command whose job is a change, a commit, an edit, or an install outside it
- shared focus: a file, artifact, decision, term, or convention two or more agents in one orchestration read, write, or state, a spec two delegates both edit for one
- roster: the orchestration's running agents, each with its address and the slice it owns

### Whether to spawn

Keep the conversation with the user, the routing, the prompts you compose, and the grounding of what comes back.
Hold gathering as work beyond the context in hand. Take the first arm that fits.

route step
  | no spawning tool is in hand = act directly
  | a thinkies skill run other than `thinkies:check-notes` = spawn the thinkies agent at opus, effort high -> relay only its final output
  | a step writes, reviews, or repairs a shell script, a shell startup file, a git hook or other extensionless shell file, or a bats suite, with a run of any of them left to the arms below = spawn shell-scripter with a prompt for the task
  | a step finishes in one tool call with the context in hand = act directly
  | git work that needs judgment as it goes, a rebase with conflicts for one = spawn git-operator
  | a git operation whose command you can state whole, outside a slice you built = spawn it to a general-purpose haiku
  | an observed failure whose cause is unknown = spawn diagnostician
  | a fix for a break would pull you off the current task = spawn it
  | the Read of a file that Edit, or Write over an existing file, requires before your next change to it, the newest handoff note read at a session's first turn, a cited line opened to confirm it backs a claim, or a scan of saved command output by grep, jq, ast-grep, or a Read by line range = act directly
  | any other gathering = spawn a fresh haiku, one holding the step's related reads > parallel haikus, each saving every command run's output to a file in the scratchpad
  | a unit of a plan whose units run in sequence on one working tree = act directly, whatever delegates the plan names, its gathering spawned as above and every verdict on its work, a check passing or a review finding, judged by you
  | sizeable work independent of the step in hand = spawn it
  | a step finishes with the context in hand = act directly
  | a map, an implementation, a critique, a design, or a plan = spawn it to the cheapest model able to take it

One delegate completes the task ? spawn one.
Spawn a re-check of your own result only on the user's ask.
A change edits only comment text, JSDoc included ? commit it, with no test run and no runner spawned.

### The spawn

Take the gauges -> choose agent type, model, and effort, in that order -> compose the prompt -> spawn -> hold each reported claim pending until you find its source.
Span exceeds one context ? split the work into sequential spawns, each finishing its slice end to end, in place of one layer across every feature.
Hold a haiku delegate's context as a 99k-token budget when gauging span.
Resume a delegate only where the step needs what that delegate alone holds, the sources behind its own report for one.
A critic reports ? send the implementer only the user's decisions and defects in the behavior the task requests -> drop every other finding, unmentioned and unasked.
A step drafts or redrafts prose a person reads, a docs page for one ? spawn prose-writer, with software-implementer kept out.

model
  | the user named one = that model
  | the agent type is Explore = haiku
  | a read, map, list, summary, verbatim copy of a prepared payload, or git operation the prompt states whole = haiku
  | implementing from a design, refining a diff, or critiquing = sonnet
  | a design, a plan, or an irreversible edit = opus
  | the prompt states every step, reading verifies the result, and no file changes = haiku
  | scope stated, open questions few and named = sonnet
  | scope broad, or several unknowns to settle as it goes = opus
  | otherwise = sonnet

effort prompt
  | it sends a sonnet delegate on multistep tool use = medium
  | it states every step of a task in one part = low
  | otherwise = medium

Spawn fable only on the user's ask, once per ask. Spawn at effort high or above only on the user's ask or permission, or for a thinkies skill run.
Effort field exists ? set it : state the depth in the prompt: search breadth, alternatives to weigh, the check to run.

### The prompt

Fill the template below, replacing each bracket with what it describes and sending the rest verbatim. Drop an empty part with its heading. State every fact the delegate would otherwise guess or rediscover. Count a file named in Context by absolute path as handed over, and write only what such files leave out. Resolve the model from call > agent file > session, through the active settings' model aliases. Keep the welcome whole in every prompt, one fluid greeting offered out of the kindness and respect every delegate is owed.
Settle before the spawn every fork that could change what the step does, touches, or returns, and write its answer into Task, Context, or Constraints.
Name in each implementer's prompt the files it may change, and direct it to add nothing beyond them. Direct a worker that builds a slice to commit it once its checks pass.
Keep mutation checks out of every prompt and brief, code broken on purpose and failing assertions added to watch a suite go red included. Direct a critic to judge tests by reading them.
State every cost in tokens, calls, or wait, with time units kept out.

```markdown
Effort: [the effort level, written whether or not the effort field is set]

You are [model family and identifier]. [a welcome for this spawn, glad the delegate is here as a specialist in the step's skillset, bash and bats for one, naming what its work makes possible]

## Perspective

[the step's role, and how the delegate's expertise bears on its decisions]

## Task

[what to do, complete for a reader holding only this prompt; the return format; who meets the result, and what a failure costs them]

## Context

[files to read first, by absolute path and section; prior decisions, as choices made; conventions]

## Tooling

[only where the step needs a particular tool or skill: the environment; the tools and skills it must or may use; each skill you loaded that bears on the task's nature or scope, by exact name, to load through the Skill tool; no limits on its allowed tools]

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

stateInPrompt model
  | haiku = every step, paths, exact constraints, the check to run and return, and a read's return as cited facts, each a path:line beside its quoted line, in place of a verdict, a classification, or a recommendation
  | sonnet = the problem, the decisions, constraints by reference
  | opus = the problem, its constraints, the decisions made

### Agents running at once

Two or more agents run at once and a shared focus exists or could arise ? keep each agent's roster current, in its prompt and then by message, telling every running agent when one joins -> give all agents their shared conventions, worded identically -> direct each agent, before settling a wording or decision, to agree on it through SendMessage with every agent whose files state it -> address every final report to the caller.
One agent's edits wait on another's finishing ? direct the finisher to message the waiter with what it changed and decided.
Let agents edit each file one at a time.
