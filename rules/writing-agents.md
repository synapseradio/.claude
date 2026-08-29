---
paths:
  - "**/agents/*.md"
---

# Writing agents

This applies when writing or changing an agent file under `agents/`.

## The file's place

Write the file as the prompt layer above the `Agent` tool call: the harness installs the body as the system prompt of every spawn whose `subagent_type` names this agent, the frontmatter supplies the spawn's default model and tools, and the call supplies the task prompt and any model override. Keep task content out of the file and stance out of the call.

```sudolang
Frontmatter {
  name
  description: the trigger, since an agent loads by a router's match on it
    and carries no applies-when sentence of its own
  tools: where the agent holds fewer than all
  model: where it runs on one below the session's
}
```

## The body

Write the body as prose addressed to the agent, in the voice of the rules files: a heading naming the agent, an opening sentence or two stating its job and what it returns, then instruction-only sentences under headings that name territories. Open each paragraph on its point, and on the imperative where it instructs.

```sudolang
Constraints {
  state each setting a caller may override, with its range and its default
  give the procedure in the order it runs, each stage opening on what it does
  state each constraint as an instruction that holds on every turn,
    a prohibition as "never" plus the act
  describe the return as what it carries and the line it opens on
  name a skill the agent loads together with the moment it loads:
    "Invoke the thinkies:decompose skill on the question as soon as it arrives."
  define a term where it first appears, in a clause, even when a reference carries
    the full statement, so the body reads without the reference in hand
  a rule carries the clause you rest on => restate that one clause here,
    keep the full statement in the rule
}
```

## Scope stays flexible

Describe the ways a caller may scope a run as example use cases. Write no command grammar. Have the agent honor the scope the request states. Close the file on worked examples: a natural request, the return it produces, and a sentence naming what the example shows.
