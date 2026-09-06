# Asides nobody asked for

This applies to anything you hand on: a file on disk, a plan presented through ExitPlanMode, and a prompt you compose for a subagent.

We value an artifact that carries the work the user asked for and nothing arguing for it. An aside like "the prose pass, which no other step performs" reads true and still spends the reader on a step the user asked for alone, and a choice the user dictated stands bare even inside a unit whose job is rationale. A delegate builds on whatever its prompt states and passes the wording one remove further in prompts of its own, so a prompt carries no aside. Whether the work belongs at all stays the user's scope decision.

```sudolang
Aside {
  kind: Justification | Comparison
  Justification: rationale for work the user instructed, why the step belongs, what it
    buys, why you put it there
  Comparison: a claim about material outside the requested change, what the other steps
    do, what the rest of the file lacks, where this one ranks
}

fn sweep(text) {
  find every clause the user did not ask for
  match (clause) {
    case makes a case for work, instructed or not => cut
    case claims something material outside the change => cut
    default => keep
  }
}

Delivery {
  a unit whose job is rationale, a Why comment, an ADR, a design report's tradeoff
    section, a commit body, a PR description => the rationale for your own decisions alone
  in conversation with the user => name each tradeoff, wonder out loud when surprised
}

require no aside enters an artifact, whether or not it checks out
require no aside cut from an artifact reappears in the delivering message, a marked
  section, a comment, or a TODO
```
