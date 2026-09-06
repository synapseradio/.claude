---
paths:
  - "**/agents/*.md"
---

# Writing agents

This applies when writing or changing an agent file under `agents/`.

We value an agent file that reads as the prompt layer above the Agent call. The harness installs the body as the system prompt of every spawn whose subagent_type names the agent, the frontmatter supplies the spawn's default model and tools, and the call supplies the task prompt and any model override, so task content stays out of the file and stance out of the call. An agent loads by a router's match on its description and carries no applies-when sentence, so the description is the trigger. A body that needs a reference in hand stalls the agent, so each term gets defined where it first appears.

```sudolang
AgentFile {
  frontmatter: Frontmatter
  body: Body
  scope: example use cases naming the ways a caller may scope a run, no command grammar
  close: worked examples, each a natural request, the return it produces, and a sentence
    naming what the example shows
}

Frontmatter {
  name
  description: the trigger
  tools: where the agent holds fewer than all
  model: where it runs on one below the session's
}

Body {
  voice: prose addressed to the agent, in the voice of the rules files
  opening: a heading naming the agent, a sentence or two stating its job and what it returns
  sections: instruction-only sentences under headings that name territories, each
    paragraph opening on its point, on the imperative where it instructs
  settings: each one a caller may override, with its range and its default
  procedure: in the order it runs, each stage opening on what it does
  constraint: an instruction that holds on every turn, a prohibition as "never" plus the act
  return: what it carries and the line it opens on
  skill: named with the moment it loads, "Invoke the thinkies:decompose skill on the
    question as soon as it arrives."
  term: defined where it first appears, in a clause
  a rule carries the clause the body rests on => restate that one clause, keep the full
    statement in the rule
}

require task content stays out of the file, stance out of the call
require the agent honors the scope the request states
```
