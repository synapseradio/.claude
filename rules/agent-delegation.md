# Delegating to an agent

This applies to every Agent call, and to every spawn a spawned agent makes in turn, one at a time.

Choose the agent type first, then the model that agent runs on and the effort it spends.

```sudolang
delegate = readings |> settings |> prompt |> spawn

Readings {
  inference: how much must the delegate infer beyond the prompt and its evidence?
  span: does the work fit one context?
  reversibility: what does undoing a wrong result cost?
  verifiability: what check outside the delegate detects a wrong answer:
    a test, a linter, a diff you read, your own verification of the report?
  survivingCritiques: which critique findings remain unrepaired?
}

settings {
  span exceeds one context => split into sequential steps first

  haiku: reads, maps, lists, summaries, stated changes verified by reading the output
  sonnet: implementing from a design, refining a diff, critiquing an artifact,
    any step no other arm matches
  opus: designs, plans, irreversible edits, repairs after a critique finding
    remained past one repair
  fable: only on the user's ask, one spawn per ask

  model = match (first case in order) {
    the user named a model => that model
    a critique finding remained past one repair => opus
    the prompt states every step && you verify the result by reading it => haiku
    later work depends on the answer && no check detects an error before then
      && undoing requires manual work => opus
    default => sonnet
  }
  two arms match equally => the cheaper, haiku < sonnet < opus

  effort = match {
    the prompt states every step => low, or medium for a task in several parts
    default => high, never above it
  }
  no effort field exposed => state the depth in the prompt:
    how wide to search, how many alternatives to weigh, what check to run
}

Prompt {
  perspective: role, expertise, why this agent for this step
  task: what to do, complete without prior context, return format named
  context: paths, prior decisions, conventions, since a delegate fills a gap
    with an invented fact, duplicated work, or a stall
  tooling: the environment, tools and skills the delegate must use, and those it may
  constraints: invariants, boundaries, what this step leaves to others
    such that it remains vertical
  invitations: permit the delegate to ask, decide, or flag where uncertain
    and say which it did, with forkAuthority stated
  a section is empty => one line naming the absence, no filler

  shape to the model:
    haiku => state every step: paths, exact constraints, the check to run and return
    opus => state the problem, its constraints, the decisions already made;
      the model chooses the steps
    sonnet => state the problem and the decisions, refer to the constraints,
      add exact context wherever the delegate would otherwise guess
}

spawn {
  set the model field on every spawn that accepts one,
    the effort field wherever one exists
  a fork's model field stays unset, so it inherits
}

forkAuthority {
  the delegate decides every fork it meets and reports what it chose,
    with two exceptions returned to the caller:
  evidence shows the prompt's stated context is wrong =>
    stop immediately, report the contradiction
  the fork depends on the user's intent, direction, or what done means =>
    return it immediately with the options it would have offered
}

receiveReport {
  every claim stays unverified until you find its source
  verify a claim carrying weight before relaying, or mark it [.?]
}
```
