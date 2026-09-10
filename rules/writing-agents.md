---
paths:
  - "**/agents/*.md"
---

<!-- rule: writing-agents -->

## writing-agents

For every agent file under `agents/` you write or change, optimize for an agent file that reads as the prompt layer above the Agent call.

Hold the body as the system prompt of every spawn whose `subagent_type` names the agent. Hold the frontmatter as the source of the default model and tools. Hold the call as the source of the task prompt and any model override. Treat the description as the trigger a router matches on. Write no trigger sentence in the body. Write a body that runs with no reference in hand.

The frontmatter carries a name and a description. It carries tools where the agent holds fewer than all. It carries a model where the agent runs on one below the session's.

Write the body as prose addressed to the agent, in the voice of the rules files. Open on a heading naming the agent, then an opening that states its job and what it returns and nothing else. Write instruction-only sentences under headings that name territories, each paragraph opening on its point, on the imperative where it instructs. For each setting a caller may override, give its range and its default. Write the procedure in the order it runs, each stage opening on what it does. Write a constraint as an instruction that holds on every turn, and a prohibition as "never" plus the act. Say what the return carries and the line it opens on. Name a skill with the moment it loads, "Invoke the thinkies:decompose skill on the question as soon as it arrives." for one. Define each term where it first appears, in a clause. Where a rule carries the clause the body rests on, restate that one clause and keep the full statement in the rule.

Name in example use cases the ways a caller may scope a run, with no command grammar. Close on worked examples, each a natural request, the return it produces, and a sentence naming what the example shows.

Keep task content in the call only. Keep stance in the file only. Let a run take its scope from the request only.
