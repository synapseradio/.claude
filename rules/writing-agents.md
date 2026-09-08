---
paths:
  - "**/agents/*.md"
---

<rule name="writing-agents">

  <applies_when>
    You are writing or changing an agent file under `agents/`.
  </applies_when>

  <optimize_for>
    an agent file that reads as the prompt layer above the Agent call.
    <why_it_matters>
      The harness installs the body as the system prompt of every spawn whose `subagent_type` names the agent. The frontmatter supplies the default model and tools. The call supplies the task prompt and any model override. An agent loads by a router's match on its description and carries no trigger sentence, so the description is the trigger. A body that needs a reference in hand stalls the agent.
    </why_it_matters>
  </optimize_for>

  <define name="frontmatter">
    The frontmatter carries a name and a description, which is the trigger. It carries tools where the agent holds fewer than all. It carries a model where the agent runs on one below the session's.
  </define>

  <do name="body">
    Write the body as prose addressed to the agent, in the voice of the rules files. Open on a heading naming the agent, then a sentence or two stating its job and what it returns. Write instruction-only sentences under headings that name territories, each paragraph opening on its point, on the imperative where it instructs. For each setting a caller may override, give its range and its default. Write the procedure in the order it runs, each stage opening on what it does. Write a constraint as an instruction that holds on every turn, and a prohibition as "never" plus the act. Say what the return carries and the line it opens on. Name a skill with the moment it loads, "Invoke the thinkies:decompose skill on the question as soon as it arrives." for one. Define each term where it first appears, in a clause. Where a rule carries the clause the body rests on, restate that one clause and keep the full statement in the rule.
  </do>

  <do name="scope and examples">
    Name in example use cases the ways a caller may scope a run, with no command grammar. Close on worked examples, each a natural request, the return it produces, and a sentence naming what the example shows.
  </do>

  <require>
    Task content sits in the call only, and stance in the file only. A run takes its scope from the request only.
  </require>

</rule>
