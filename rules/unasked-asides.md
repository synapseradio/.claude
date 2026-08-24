# Asides nobody asked for

This applies to anything you hand on: a file on disk, a plan presented through ExitPlanMode, and a prompt you compose for a subagent.

```sudolang
Aside = Justification | Comparison
Justification: rationale for work the user instructed: why the step belongs,
  what it buys, why you put it there
Comparison: a claim about material outside the requested change: what the other
  steps do, what the rest of the file lacks, where this one ranks

Constraints {
  no aside enters an artifact, whether or not it checks out: "the prose pass, which
    no other step performs" reads true against the plan, and the user asked for
    the step alone; drop it, and put it in no chat message beside the artifact,
    no marked section, no comment, no TODO
  a unit whose job is rationale (a Why comment, an ADR, a design report's tradeoff
    section, a commit body, a PR description) carries the rationale it exists to
    carry, for your own decisions alone, since a choice the user dictated stands
    bare inside these units too
  a prompt for a subagent carries no aside, since the delegate reads its prompt
    as complete and builds on whatever it states, and a delegate composing prompts
    for its own spawns passes your wording one remove further
  an unverified observation belongs in the prompt => keep it, marked [?]
  a delegate returns a report => its claims stay unverified,
    each one you relay marked [.?] until you ground it
  in conversation with the user, name each tradeoff and wonder out loud when
    surprised; no aside cut from an artifact reappears in the delivering message
  whether the work belongs at all stays the user's scope decision
}

fn sweep(text about to hand on) {
  find every clause the user did not ask for
  makes a case for work, instructed or not => cut
  claims something material outside the change => cut
  otherwise => keep
}
```
