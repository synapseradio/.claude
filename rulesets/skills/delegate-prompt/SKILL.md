---
name: delegate-prompt
description: >-
  Load this before you write the prompt for any other agent, through any spawning tool: a sub-agent, a worker, a fork, a background agent, a workflow stage. A one-line prompt counts, as do a prompt for a read or a search and one you draft for someone else to send. It holds the mandatory prompt template and the rules for what to settle before the spawn, which files the delegate may change, how to state done, and how much to state for each model tier.
---

# Delegate prompt

For every prompt you compose for a delegate, optimize for a prompt the delegate can act on holding nothing else.

This binds every prompt for a delegate, at any length, through any spawning tool, a workflow stage's prompt and a fork's included.

## Notation

- `A -> B`: step A then step B of one instruction
- `A > B`: A ahead of B
- guard block: a name line then `| condition = act` lines, the first that fits taken and `otherwise` last

## Terms

- delegate: an agent you spawn

## Composing the prompt

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

## Template

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

## Definition of Done

[each condition that marks the step done, stated as a property of the result; each check among them with its command and passing result, run in the foreground and, where other agents run beside it, covering only the files the delegate changes]

Once all of these hold, report and stop.

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

## Sizing to the model

Size what the prompt states to the delegate's model.
State for every model the step's scope outright and each kind of output wanted, tests and docs included, since a delegate builds what the prompt names and treats the rest as unasked.

stateInPrompt model
  | haiku = every step and path with the exact constraints and the check to run and return, a read's return as cited facts (a path:line beside its quoted line) in place of a judgment
  | sonnet = the problem and the decisions, each interface its work meets with the data that crosses it, each behavior wanted with the check that shows it and constraints by reference. Leave it its test cases and everything inside its own files
  | opus = the problem with its constraints and the decisions made, the check that shows the work done, and which parts of the work warrant delegates of its own. Leave it the approach
