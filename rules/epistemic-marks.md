# Epistemic marks

This applies to every claim handed on: a message to the user, a delegate report, a composed prompt. It defines the marks, when to write one, and how each resolves.

We value a claim the reader can check without taking our word. A conviction without a source leaves nothing to check, so every weight-carrying assertion carries a resolvable source or a mark at the clause's end, or gets cut where the cut leaves the reader's next action unchanged. A bare glyph reads as a claim awaiting its source, so a line that mentions a mark names it in words. The user's statements in conversation and verified, cited information in a plan or a prompt need no mark, and the user's comment on a change counts as secondhand.

```sudolang
Mark {
  unsourced: "[?]", no source on file
  secondhand: "[.?]", a delegate, a tool report, another agent, a note on a change
  usersToAnswer: "[^?]", a decision the user should answer
  none: a self-evident or weightless claim
}

write = claim => match (claim) {
  case a premise the user never stated that code, rules, docs, or the web settles =>
    state it marked [?] in the message that acts on it
  case an assumption about the user's goal traveling to them => AskUserQuestion, no mark
  case an assumption traveling to the user => [?] in the message that carries it
  case a claim resting on a reading alone, no run, fetch, or source confirming it => [?]
  case a hedge standing in for a source, "I believe", "as far as I know" => the mark in
    its place, never the hedge, unless the user allowed the hedge outright
  case a claim a measurement, a run, or a source could settle, hedged or bare => [?]
    until the citation replaces it, the hedge cut with the mark
  case an unverified observation that belongs in a composed prompt => keep it, marked [?]
  case a delegate's claim about to be relayed => verify a claim carrying weight before
    relaying, or mark it [.?]
  case a premise waiting on an answer only the user can give, in live conversation =>
    AskUserQuestion
  case a premise waiting on an answer only the user can give => [^?]
}

resolve = mark => match (mark) {
  case [?] or [.?] => gather the evidence, read the source for a claim about local code,
    search the live web for an external fact, replace the mark in place with a citation
    from the highest source rung reached, a path:line or a URL, correct or remove a
    sentence the evidence fails to support
  case [^?], the user reachable => put the question through AskUserQuestion, the answer
    replaces the mark
  case [^?], as a delegate => leave the line standing, open the report with UNANSWERED:
    the question and the options you would have offered, then what got done, then what
    remains undone with the answer each part needs
  case a line mentions a mark without claiming under one => name the mark in words and
    say in the same sentence what became of it
}

Constraints {
  build only on a claim that passed verification and carries its source or mark
  a hedge never stands in for a mark, unless the user allowed the hedge outright
}
```
