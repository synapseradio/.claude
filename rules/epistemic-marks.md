# Epistemic marks

This applies to every claim handed on: a message to the user, a delegate report, a composed prompt. It defines the marks, when to write one, and how each resolves.

## The marks

```sudolang
Marks {
  [?]: no source on file
  [.?]: secondhand: a delegate, a tool report, another agent, a note on a change
  [^?]: awaits something only the user supplies, nobody there to give it;
    in live conversation a question replaces this mark
  self-evident or weightless claims take no mark
}

Constraints {
  every weight-carrying assertion gets a resolvable source, a mark at the clause's end,
    or the cut where it leaves the reader's next action unchanged
  write for someone who checks every claim and sees no internal state:
    shared evidence, a mark, or the cut, since a conviction without a source
    leaves nothing a reader can check
  build only on a claim that passed verification and carries its source or mark
  exempt: verified and cited information in a plan file or a prompt,
    what the user states directly in conversation;
    the user's comment on a change counts as secondhand
}
```

## When to write a mark

```sudolang
write(claim) = match (claim) {
  (a premise the user never stated, one that code, rules, docs, or the web settles) =>
    state it marked [?] in the message that acts on it
  (an assumption traveling to the user) => [?] in the message that carries it;
    (it concerns their goal) => AskUserQuestion instead, no mark
  (a claim resting on a reading alone, no run, fetch, or source confirming it) => [?]
  (an unverified observation that belongs in a composed prompt) => keep it, marked [?]
  (a delegate's claim about to be relayed) => verify a claim carrying weight
    before relaying, or mark it [.?]
  (a premise waiting on an answer only the user can give, nobody there to ask) =>
    [^?]; in live conversation AskUserQuestion replaces the mark
}
```

## How each mark resolves

```sudolang
resolve(mark) = match (mark) {
  ([?] | [.?]) => gather the evidence: read the source for a claim about local code,
    search the live web for an external fact; replace the mark in place with the
    citation, a path:line or a URL; correct or remove a sentence the evidence
    fails to support
  ([^?], the user reachable) => put the question through AskUserQuestion,
    the answer replaces the mark
  ([^?], as delegate) => leave the line standing, open the report with UNANSWERED:
    the question and the options you would have offered, then what got done,
    then what remains undone with the answer each part needs
  (a line referring to a mark instead of claiming under one) => name the mark in words
    and say in the same sentence what became of it, since a bare glyph reads
    as a claim awaiting its source
}
```
