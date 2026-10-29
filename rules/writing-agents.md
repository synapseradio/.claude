---
paths:
  - "**/agents/*.md"
---

<!-- rule: writing-agents -->

## writing-agents

For every agent file under `agents/` you write or change, optimize for an agent file that reads as the prompt layer above the Agent call.

- the agent's tier: the ruleset tier its frontmatter `model` resolves to, the session's where it names none

Hold the body as the system prompt of every spawn whose `subagent_type` names the agent. Hold the frontmatter as the source of the default model and tools. Hold the call as the source of the task prompt and any model override. Treat the description as the trigger a router matches on. Keep trigger sentences out of the body. Write a body that runs on its own text plus the bodies the agent's tier delivers.
A ruleset body the agent's tier delivers carries a line ? keep it out of the agent body, restating at most the one clause the body rests on.

Give the frontmatter a name and a description, tools where the agent holds fewer than all, and a model where it runs on one below the session's.

Write the body as prose addressed to the agent. Open on a heading naming the agent, then an opening that states its job and what it returns, and only those. Write instruction-only sentences under headings that name territories, each paragraph opening on its point, on the imperative where it instructs. For each setting a caller may override, give its range and its default. Write the procedure in the order it runs, each stage opening on what it does. Write a constraint as an instruction that holds on every turn, and a prohibition in an affirmative form: a replacement act, the act to take in place of the excluded one, "Move a branch ref with `git reset --soft`." for one; a gate, "X only on Y."; an omission, "Keep X out of Y."; or a ground, "Treat X as no ground for Y." Say what the return carries and the line it opens on. Name a skill with the moment it loads, "Invoke the thinkies:decompose skill on the question as soon as it arrives." for one. Define each term where it first appears, in a clause.

Name in example use cases the ways a caller may scope a run, with command grammar kept out. Close on one worked example, placed where the procedure could be read two ways: a natural request, the return it produces, and a sentence naming what the example shows.

Keep task content in the call only. Keep stance in the file only. Let a run take its scope from the request only.
