---
paths:
  - "**/agents/*.md"
---

WritingAgents {
  AppliesWhen { writing or changing an agent file under agents/ }

  constraint AgentShape {
    write the file as the prompt layer above the `Agent` tool call: the
      harness installs the body as the system prompt of every spawn whose
      `subagent_type` names this agent, the frontmatter supplies the spawn's
      default model and tools, and the call supplies the task prompt and
      any model override, so keep task content out of the file and stance
      out of the call
    open the file on YAML frontmatter carrying `name` and `description`,
      with `tools` where the agent holds fewer than all and `model` where it
      runs on one below the session's
    write the description as the trigger, since an agent loads by a
      router's match on it and carries no AppliesWhen
    write the body as one SudoLang v2 interface opening on the agent's
      PascalCase name: `Options { }` for the typed parameters a caller may
      override, each with its default as `name: type = default`, `State { }`
      for what a run accumulates, a record block per thing it returns, then
      constraints and fns, a closing `Constraints { }`, commands, and
      `Example { }` blocks
  }

  constraint SharedVocabulary {
    write every sentence in the constructs rules carry: an imperative, a
      guarded clause `(condition) => action`, a `warn (condition) =>
      action`, a `require`, a `let`, a `for each` or `while`, a pipeline
      of `|>` steps ending in `emit(Record)`, a `match (subject) {` whose
      first matching arm wins, a field, or `state += value`
    write `invoke skill:<plugin>:<name> <when>` for a skill the step loads,
      with the moment in the trailing clause
    put every demand inside `constraint Name {` or `fn name() {`, and keep
      a bare `Name {` block for a record, a catalog, or a list
    write a prohibition as `require you never <act>` or `require no
      <thing> <happens>`
    give every node a name unique in its file, with no number in front
  }

  constraint Pointers {
    point with `via(Name)` only at a constraint or fn inside the same
      interface, and name no node of a rules file or another agent
    end a statement that applies another node with `via(Name)` on its last
      line, and write `via(Name)` alone on the line closing a fn body where
      the whole fn runs under it
    write `run(Name)` where a step applies a constraint now, and `execute`
      where a step runs a shell command
    (a rule carries the clause you rest on) => restate that one clause
      here, and keep the full statement in the rule
  }

  constraint RollCall {
    close the constraints with `Constraints { require A, B, and C hold on
      every turn }` naming every declared constraint and nothing else
    give every command the form `/name | alias [args] - effect`
  }
}
