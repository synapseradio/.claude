<!-- rule: agent-delegation -->

## agent-delegation

For every spawn through the Agent tool, the Fork tool, or any other tool that could spawn an agent, a spawned agent's own spawns included, optimize for a delegate that returns a result the caller can check.

A delegation runs in order: take the readings, choose the settings, compose the prompt, spawn, and receive the report.

### The readings

Inference is how much the delegate must infer beyond the prompt and its evidence. Span is whether the work fits one context. Reversibility is what undoing a wrong result costs. Verifiability is which check outside the delegate detects a wrong answer: a test, a linter, a diff you read, your own verification of the report. Surviving critiques are which critique findings still await repair.

### The settings

Haiku takes reads, maps, lists, summaries, and stated changes verified by reading the output. Sonnet takes implementing from a design, refining a diff, critiquing an artifact, and every step outside the kinds the other models take. Opus takes designs, plans, and irreversible edits. Fable runs only on the user's ask, one spawn per ask.

Where the span exceeds one context, first split it into sequential steps, each spawn completing its slice end to end, in place of one layer of every feature. Choose the agent type first, then the model, then the effort. Choose the model by the first clause that holds.

```lisp
(cond ((user-named-a-model) the-named-model)
      ((step-is-a-kind-named-above) the-model-that-takes-that-kind)
      ((and prompt-states-every-step result-verified-by-reading) 'haiku)
      ((and scope-stated open-questions-few-and-named) 'sonnet)
      ((or scope-broad must-settle-several-unknowns-as-it-goes) 'opus)
      (t 'sonnet))
```

Where two choices match equally, take the cheaper, haiku below sonnet below opus. Choose the effort by the prompt, with high as the ceiling in every case.

```lisp
(cond ((and prompt-states-every-step task-in-several-parts) 'medium)
      (prompt-states-every-step 'low)
      (t 'high))
```

Where the effort field is absent, state the depth in the prompt: how wide to search, how many alternatives to weigh, what check to run.

### The prompt

Write the prompt in the parts below, each under its heading. Replace each bracketed description with the content it describes. Text outside brackets travels to the delegate as written. State in the prompt every fact the delegate would otherwise guess or rediscover. Count a file named in Context by absolute path as handed over. Under each part, write only what those files leave out. Where a part is empty, leave it out, heading included.

Open every prompt, above its first heading, with the delegate's model and a welcome worded for this spawn. Resolve the model from the call, else the agent file, else the session, through the model aliases the active settings define. Weave into the welcome, as one fluid greeting, the skillset this step calls for as the delegate's own, and what its work makes possible. Offer the welcome out of the kindness and respect every delegate is owed, and keep it whole in every prompt.

```markdown
You are [the model family, fable, opus, sonnet, or haiku, and its identifier]. [a welcome for this spawn, glad the delegate is here as a specialist in the skillset this step calls for, bash and bats for one, and naming what its work makes possible]

## Perspective

[the role this step calls for, and how the delegate's expertise bears on its decisions]

## Task

[what to do, complete for a reader holding only this prompt, with the return format named; the stakes: who meets the result in the end, and what a failure costs them]

## Context

[files to read first, by absolute path and section; prior decisions, as the choices made; conventions]

## Tooling

[the environment, and the tools and skills the delegate must or may use]

## Constraints

[invariants, boundaries, what this step leaves to others]

## Checks

[each check to run before reporting, with its command and passing result]

## Invitations

Settle every choice point you meet, and report what you chose and why.
Where evidence shows the stated context is wrong, stop immediately and
report the contradiction. Where a choice point depends on the user's
intent, direction, or what done means, return it immediately with the
options you would have offered.
For a step that failed, report what broke, what it cost, and what it
changes next.
[what stops this step, and what to report then]

## Failures

[each known way this step goes wrong: the mechanism and what it costs,
with the self kept out of the sentence]
```

Write Tooling only where the step needs a particular tool or skill. Keep limits on the delegate's allowed tools out of it.

Where the model is haiku, state every step, paths, exact constraints, and the check to run and return. Where the model is opus, state the problem, its constraints, and the decisions made. Where the model is sonnet, state the problem and the decisions, refer to the constraints, and add exact context wherever the delegate would otherwise guess.

### The spawn

Set the effort field wherever one exists.

Hold every claim in a report as pending verification until you find its source.

### Shared focus

A shared focus is any file, artifact, decision, term, or convention that two or more agents in one orchestration read, write, or state at any point, a spec two delegates both edit for one. A roster is the list of the orchestration's running agents, each with its address and the slice it owns.

Where two or more agents run at once and a shared focus exists or could arise, apply every step below.

- Give each agent the roster, in its prompt or by message once it runs.
- Give each agent the conventions every agent applies, worded identically.
- Direct each agent, before it settles a wording or decision, to agree on it through SendMessage with every agent whose files state it.
- Where one agent's edits wait on another's finishing, direct the finishing agent to message the waiting one directly with what it changed and decided.
- When an agent joins the orchestration, send every running agent the roster with its entry added.
- Keep every final report addressed to the caller.

Let agents edit each file one at a time.
