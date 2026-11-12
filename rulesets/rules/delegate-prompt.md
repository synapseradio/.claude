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
