# Delegating to an agent

This applies to every Agent call, and to every spawn a spawned agent makes in turn, one at a time.

Choose the agent type first, then the model that agent runs on and the effort it spends. Delegation runs in four steps: take readings from the task, choose settings, compose the prompt, spawn.

## Readings

Answer five questions from the task. Inference: how much must the delegate infer beyond what the prompt and its evidence state? Span: does the work fit one context? Reversibility: what does undoing a wrong result cost? Verifiability: what check outside the delegate detects a wrong answer, whether a test, a linter, a diff read by you, or your own verification of the report? Surviving critiques: which critique findings remain unrepaired?

## Settings

When the span exceeds one context, split the task into sequential steps first.

Each model has its uses. Haiku takes reads, maps, lists, summaries, and stated changes you verify by reading the output. Sonnet takes implementing from a design, refining a diff, critiquing an artifact, and any step no other arm matches. Opus takes designs, plans, irreversible edits, and repairs after a critique finding remained past one repair. Fable runs only when the user asks, one spawn per ask.

Pick the model by case, in this order. The user named a model: that model. A critique finding remained past one repair: opus. The prompt states every step, and you verify the result by reading it: haiku. Later work depends on the answer, no check detects an error before then, and undoing it requires manual work: opus. Otherwise: sonnet. When two arms match equally, take the cheaper model, with haiku below sonnet below opus.

Pick the effort by inference. When the prompt states every step, use low, or medium for a task in several parts. Otherwise use high, and never above it. When the spawn exposes no effort field, state the depth in the prompt: how wide to search, how many alternatives to weigh, what check to run.

## The prompt

Fill six sections, and where a section is empty, write one line naming the absence and no filler. Perspective: role, expertise, and why this agent for this step. Task: what to do, complete without prior context, with the return format named. Context: paths, prior decisions, and conventions, since a delegate fills a gap with an invented fact, duplicated work, or a stall. Tooling: the environment, tools and skills the delegate must use, and those it may. Constraints: invariants, boundaries, and what this step leaves to others such that it remains vertical. Invitations: permit the delegate to ask, decide, or flag where it is uncertain and to say which it did, with the fork authority below stated.

Match the prompt to the model. For haiku, state every step: exact (or inexact) paths, exact constraints, the check to run and return. For opus, state the problem, its constraints, and the decisions already made, and let the model choose the steps. For sonnet, state the problem and the decisions, refer to the constraints, and add exact context wherever the delegate would otherwise guess.

## Spawning

Set the model field on every spawn that accepts one, and the effort field wherever one exists. Leave a fork's model field unset, so it inherits.

## Fork authority

Let the delegate decide every fork it meets during the run, and have it report what it chose, with two exceptions it returns to the caller. When evidence shows the prompt's stated context is wrong, the delegate stops immediately and reports the contradiction. When the fork depends on the user's intent, direction, or what done means, the delegate immediately returns it to the caller with the options it would have offered.

## Receiving a report

Treat every claim in a report as unverified until you find its source. Verify a claim carrying weight before relaying it, or mark it `[.?]`.
