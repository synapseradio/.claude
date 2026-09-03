# Writing comments

This applies to every comment in source code.

Take a comment as the last resort. Reach for one only after a name, a type, a test, and a document have each failed to carry what needs saying.

Never state an invariant in a comment. Put it in a type, a test, or a name, and in documentation where those cannot hold all of it. Explain why an invariant holds only in a comment the user approved, asked for directly before you write it.

Treat a Contract comment as a code smell. A contract belongs in at least two of tests, types, names, documentation. Write one only where a type and every static analysis tool the project runs cannot make the same guarantee, and where documentation that does or should exist fails to replace it.

```sudolang
route(knowledge) = match {
  does not outlive the code beside it (today's change, the bug, the date) =>
    the commit, the PR, or the ticket, and no comment
  fits a name, a type, a test, or a doc => put it there, and no comment
  states what the code does => improve the code until the would-be comment
    falls away, and no comment
  states an invariant => write the type, the test, or the name that carries it,
    and no comment
  explains why an invariant holds => ask the user, write nothing until they approve
    the comment
  warns of a hazard => write the test that fails on contact with it, and no comment
  fits one of the five kinds below => write that kind, bound to one point,
    on its referent
  default => write nothing
}

CommentKind {
  Why: rationale
  Contract: a unit's promise to its caller, worded so the caller trusts
    the interface unread, written only where a type and every static analysis tool
    the project runs cannot make that promise
  Consult: the person or group to talk to before this code changes, written only
    where the user names them for a codebase with several owners
  Anchor: the domain fact the code answers to, citing its protocol, spec, or regulation
  Map: orientation otherwise rebuilt by hand, a state layout or the key idea
    behind a non-obvious algorithm
}

Constraints {
  word it to hold now, for as long as the code stands: no date, no version, no "was",
    "will", "for now", "currently", "still", or "soon"
  a banner marking a moment => ask first
  every external referent carries an http(s) link, never a disk path or a line number
    unless the user asks
  an invariant worth enforcing => write the test that checks it
  that test cannot land in this change => a TODO with an owner or ticket
  knowledge spans more than one file => put it in docs, point the comment there
  draft the interface comment before the body
  it will not stay short => fix the design until it shrinks
  an edit brings a nearby comment within reach => hold it to this rule, removing one
    that restates its neighbors or contradicts the code in the same edit
  a convention mandates a comment on every declaration => the one sentence a caller
    needs, plus what static analysis and IDE tooling require: JSDoc with type
    signatures under @ts-check, and the like
  in doubt, leave it out
  sure it belongs => keep it concise
}
```
