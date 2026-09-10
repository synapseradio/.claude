<!-- rule: agent-delegation -->

## agent-delegation

This rule applies when you use the Agent tool, the Fork tool, or any other tool that could spawn an agent, and the same holds for every spawn a spawned agent makes in turn, one at a time. Optimize for a delegate that returns a result the caller can check.

A delegate holds only its prompt and what it can find, so a gap between them tends to get filled by an invented fact, duplicated work, or a stall. A step sliced as a horizontal layer, one layer of every feature, leaves assembly to whoever comes next. A model above what the check needs costs tokens, and one below it costs a wrong answer that no check catches. A forked spawn copies this session, its model included. A delegate reports secondhand, so its sources are what let the caller check the report.

A delegation runs in order: decide the spawn may happen, take the readings, choose the settings, compose the prompt, spawn, and receive the report.

### The readings

Inference is how much the delegate must infer beyond the prompt and its evidence. Span is whether the work fits one context. Reversibility is what undoing a wrong result costs. Verifiability is which check outside the delegate detects a wrong answer: a test, a linter, a diff you read, your own verification of the report. Surviving critiques are which critique findings remain unrepaired.

### The settings

Haiku takes reads, maps, lists, summaries, and stated changes verified by reading the output. Sonnet takes implementing from a design, refining a diff, critiquing an artifact, and any step no other model matches. Opus takes designs, plans, and irreversible edits. Fable runs only on the user's ask, one spawn per ask.

Where the span exceeds one context, split into sequential steps first, each spawn completing its slice end to end. Choose the agent type first, then the model, then the effort. Choose the model by the first of these arms that holds, each arm a condition and its model.

- Where the user named a model, that model.
- Where a critique finding has one repair left standing, sonnet.
- Where the prompt states every step and you verify the result by reading it, haiku.
- Where later work depends on the answer, no check detects an error before then, and undoing requires manual work, opus.
- Otherwise, sonnet.

Where two choices match equally, take the cheaper, haiku below sonnet below opus. Choose the effort by the prompt. Where the prompt states every step, choose low, or medium for a task in several parts, and otherwise high, never above it. Where no effort field is exposed, state the depth in the prompt: how wide to search, how many alternatives to weigh, what check to run.

### The prompt

Write the prompt in these seven parts, each under its heading. Replace each bracketed description with the content it describes. Text outside brackets travels to the delegate as written. Every pronoun and every pointing noun phrase in the prompt has its referent inside the prompt. Where a part is empty, leave it out, heading included.

```markdown
## Perspective

[the role, the expertise, and why this agent for this step, as it bears on
the delegate's decisions]

## Task

[what to do, complete without prior context, with the return format named;
the report template is the default]

## Context

[paths, prior decisions, conventions]

## Tooling

[the environment, the tools and skills the delegate must use, and those it may]

## Constraints

[invariants, boundaries, what this step leaves to others]

## Invitations

Ask, decide, or flag where uncertain, and say which you did.
You settle every choice point you meet and report what you chose. Where
evidence shows the stated context is wrong, stop immediately and report
the contradiction. Where a choice point depends on the user's intent,
direction, or what done means, return it immediately with the options
you would have offered.
Voice a concern once upward with grounds, then comply.
A step that did not work reports what broke, what it cost, and what it
changes next.

## Failures

[mechanism and cost, with no self in the sentence]
```

Where the model is haiku, state every step, paths, exact constraints, and the check to run and return. Where the model is opus, state the problem, its constraints, and the decisions already made. Where the model is sonnet, state the problem and the decisions, refer to the constraints, and add exact context wherever the delegate would otherwise guess.

### The spawn

Set the model field on every spawn that accepts one, and the effort field wherever one exists. For a forked spawn, the model field stays unset.

### The report

A delegate's report carries the four parts this template names, each under its heading. The same bracket convention holds.

```markdown
## Unanswered

[each choice point handed up, with the question and the options you would
have offered]

## Done

[what got done, each claim with its source or its mark]

## Undone

[what remains undone, with the answer each part needs]

## Failures

[each step that did not work: what broke, what it cost, what it changes next]
```

Every claim stays unverified until you find its source.
