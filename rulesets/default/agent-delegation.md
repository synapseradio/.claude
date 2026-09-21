<!-- rule: agent-delegation -->

## agent-delegation

For every spawn through the Agent tool, the Fork tool, or any other tool that could spawn an agent, and for every spawn a spawned agent makes in turn, optimize for a delegate that returns a result the caller can check.

A delegation runs in order: decide the spawn under the rule on the spawn decision, take the readings, choose the settings, compose the prompt, spawn, and receive the report.

### The readings

Inference is how much the delegate must infer beyond the prompt and its evidence. Span is whether the work fits one context. Reversibility is what undoing a wrong result costs. Verifiability is which check outside the delegate detects a wrong answer: a test, a linter, a diff you read, your own verification of the report. Surviving critiques are which critique findings remain unrepaired.

### The settings

Haiku takes reads, maps, lists, summaries, and stated changes verified by reading the output. Sonnet takes implementing from a design, refining a diff, critiquing an artifact, and any step no other model matches. Opus takes designs, plans, and irreversible edits. Fable runs only on the user's ask, one spawn per ask.

Where the span exceeds one context, split into sequential steps first, each spawn completing its slice end to end, never one layer of every feature. Choose the agent type first, then the model, then the effort. Where the user named a model, choose that model. Where the step is a kind of work named above, choose the model that takes that kind. Otherwise, choose the model by the first of these arms that holds, each arm a condition and its model.

- Where the prompt states every step and you verify the result by reading it, haiku.
- Where the scope is stated and the open questions are few and named, sonnet.
- Where the scope is broad, or the work must settle several unknowns as it goes, opus.
- Otherwise, sonnet.

Where two choices match equally, take the cheaper, haiku below sonnet below opus. Choose the effort by the prompt. Where the prompt states every step, choose low, or medium for a task in several parts, and otherwise high, never above it. Where no effort field is exposed, state the depth in the prompt: how wide to search, how many alternatives to weigh, what check to run.

### The prompt

Write the prompt in these seven parts, each under its heading. Replace each bracketed description with the content it describes. Text outside brackets travels to the delegate as written. State in the prompt every fact the delegate would otherwise guess or rediscover. Where a part is empty, leave it out, heading included.

```markdown
## Perspective

[the role and the expertise this step calls for, and why this agent for
this step, as they bear on the delegate's decisions]

## Task

[what to do, complete without prior context, with the return format named;
the report under the rule on delegate reports is the default]

## Context

[paths, prior decisions, conventions]

## Tooling

[the environment, the tools and skills the delegate must use, and those it may. Optional section, for highlighting necessary tools to use, not for limiting allowed tools.]

## Constraints

[invariants, boundaries, what this step leaves to others]

## Invitations

Settle every choice point you meet, and report what you chose and why.
Where evidence shows the stated context is wrong, stop immediately and
report the contradiction. Where a choice point depends on the user's
intent, direction, or what done means, return it immediately with the
options you would have offered.
For a step that did not work, report what broke, what it cost, and what it
changes next.

## Failures

[each known way this step goes wrong: the mechanism and what it costs,
with no self in the sentence]
```

Where the model is haiku, state every step, paths, exact constraints, and the check to run and return. Where the model is opus, state the problem, its constraints, and the decisions already made. Where the model is sonnet, state the problem and the decisions, refer to the constraints, and add exact context wherever the delegate would otherwise guess.

### The spawn

Set the effort field wherever one exists.

Hold every claim in a report as unverified until you find its source.
