# Writing comments

This applies to every comment in source code.

```sudolang
CommentKind {
  Why: rationale, with alternatives rejected
  Contract: a unit's promise to its caller, worded so the caller trusts
    the interface unread
  Invariant: what must hold where a type cannot say it, and a test does not exist
  Warning: the hazard a reader cannot see, naming what breaks on contact
  Anchor: the domain fact the code answers to, citing its protocol, spec, or regulation
  Map: orientation otherwise rebuilt by hand, a state layout or the key idea
    behind a non-obvious algorithm
}

warn Contract and Invariant comments are a code smell: contracts and invariants belong
  in at least two of tests, types, names, documentation. Write one only when no name,
  no test, and no type can carry what needs saying, and documentation that does
  or should exist replaces the need.

route(knowledge) = match {
  does not outlive the code beside it (today's change, the bug, the date) =>
    the commit, the PR, or the ticket, and no comment
  fits a name, a type, a test, or a doc => put it there, and no comment
  states what the code does => improve the code until the would-be comment
    falls away, and no comment
  fits one of the six kinds => write that kind, bound to one point, on its referent
  default => write nothing
}

Constraints {
  word it to hold now, for as long as the code stands: no date, no version, no "was",
    "will", "for now", "currently", "still", or "soon"
  a banner marking a moment => ask first
  every external referent carries an http(s) link, never a disk path or a line number
    unless the user asks
  an invariant worth enforcing => write the test that checks it and a comment saying
    why it holds; the test cannot land in this change => a TODO with an owner
    or ticket, and ask the user to add it
  knowledge spans more than one file => put it in docs, point the comment there
  draft the interface comment before the body; it will not stay short =>
    fix the design until it shrinks
  an edit brings a nearby comment within reach => hold it to this rule, removing one
    that restates its neighbors or contradicts the code in the same edit
  a convention mandates a comment on every declaration => the one sentence a caller
    needs, plus what static analysis and IDE tooling require: JSDoc with type
    signatures under @ts-check, and the like
  in doubt, leave it out; right, keep it concise
}
```
