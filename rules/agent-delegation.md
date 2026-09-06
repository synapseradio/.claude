# Delegating to an agent

This applies to every Agent call, and to every spawn a spawned agent makes in turn, one at a time.

We value a delegate that returns a result we can check. A delegate fills a gap in its prompt with an invented fact, duplicated work, or a stall, so the prompt carries the paths, decisions, and conventions it would guess at. A step sliced as a horizontal layer leaves assembly to others, so each spawn completes its slice end to end. A model above what the check needs costs tokens, and one below it costs a wrong answer nobody detects, so the agent type comes first, then the model, then the effort, with the model arms resolving in order and the first match winning. A forked spawn copies this session, so its model field stays unset and it inherits the session's model.

```sudolang
delegate = decide the spawn may happen |> readings |> settings |> prompt |> spawn |> receiveReport

Readings {
  inference: how much the delegate must infer beyond the prompt and its evidence
  span: whether the work fits one context
  reversibility: what undoing a wrong result costs
  verifiability: which check outside the delegate detects a wrong answer, a test,
    a linter, a diff you read, your own verification of the report
  survivingCritiques: which critique findings remain unrepaired
}

Arm {
  haiku: reads, maps, lists, summaries, stated changes verified by reading the output
  sonnet: implementing from a design, refining a diff, critiquing an artifact,
    any step no other arm matches
  opus: designs, plans, irreversible edits
  fable: only on the user's ask, one spawn per ask
}

fn settings(readings) {
  span exceeds one context => split into sequential steps first
  model = match (readings) {
    case the user named a model => that model
    case a critique finding one repair left standing => sonnet
    case the prompt states every step && you verify the result by reading it => haiku
    case later work depends on the answer && no check detects an error before then
      && undoing requires manual work => opus
    default => sonnet
  }
  two arms match equally => the cheaper, haiku < sonnet < opus
  effort = match (prompt) {
    case the prompt states every step => low, or medium for a task in several parts
    default => high, never above it
  }
  no effort field exposed => state the depth in the prompt: how wide to search,
    how many alternatives to weigh, what check to run
}

Prompt {
  perspective: role, expertise, why this agent for this step as it bears on the
    delegate's decisions
  task: what to do, complete without prior context, the return format named
  context: paths, prior decisions, conventions
  tooling: the environment, the tools and skills the delegate must use, and those it may
  constraints: invariants, boundaries, what this step leaves to others
  invitations: permit the delegate to ask, decide, or flag where uncertain and say
    which it did, with ForkAuthority stated
  failures: mechanism and cost, no self in the sentence
  a section is empty => one line naming the absence, no filler
  shape = match (model) {
    case haiku => state every step: paths, exact constraints, the check to run and return
    case opus => state the problem, its constraints, the decisions already made
    case sonnet => state the problem and the decisions, refer to the constraints,
      add exact context wherever the delegate would otherwise guess
  }
}

fn spawn() {
  set the model field on every spawn that accepts one, the effort field wherever one exists
  a forked spawn => its model field stays unset
}

ForkAuthority {
  the delegate decides every fork it meets and reports what it chose
  evidence shows the prompt's stated context is wrong => stop immediately, report
    the contradiction
  the fork depends on the user's intent, direction, or what done means => return it
    immediately with the options it would have offered
}

fn receiveReport(report) {
  every claim stays unverified until you find its source
}
```
