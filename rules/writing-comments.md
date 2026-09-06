# Writing comments

This applies to every comment in source code.

We value a comment written after the code itself, a name, a type, a test, and a document have each failed to carry what needs saying. An invariant in a comment goes unchecked where a type, a test, or a name checks it, so no invariant lands in a comment, and its why lands only in a comment the user asked for and approved. A contract belongs in at least two of tests, types, names, and documentation, so a Contract comment is a code smell, and a comment worded to a moment goes stale while the code stands.

```sudolang
route = knowledge => match (knowledge) {
  case does not outlive the code beside it, today's change, the bug, the date =>
    the commit, the PR, or the ticket, and no comment
  case fits a name, a type, a test, or a doc => put it there, and no comment
  case states what the code does => improve the code until the would-be comment falls away
  case states an invariant => the type, the test, or the name that carries it, and no comment
  case explains why an invariant holds => ask the user, write nothing until they approve
  case warns of a hazard => the test that fails on contact with it, and no comment
  case spans more than one file => docs, with the comment pointing there
  case a promise a type or a static analysis tool the project runs can make => no
    Contract comment
  case a promise documentation that does or should exist replaces => no Contract comment
  case a person or group to consult the user never named => no Consult comment
  case fits a CommentKind => that kind, bound to one point, on its referent
  default => write nothing
}

CommentKind {
  Why: rationale
  Contract: a unit's promise to its caller, worded for a caller who reads the interface
    and nothing else
  Consult: the person or group the user names to talk to before this code changes, in a
    codebase with several owners
  Anchor: the domain fact the code answers to, citing its protocol, spec, or regulation
  Map: orientation otherwise rebuilt by hand, a state layout or the key idea behind
    a non-obvious algorithm
}

fn write(comment) {
  draft the interface comment before the body
  word it to hold for as long as the code stands: no date, no version, no "was", "will",
    "for now", "currently", "still", or "soon"
  every external referent carries an http or https link; the user asks for a disk path
    or a line number => that
  a banner marking a moment => ask first
  it will not stay short => fix the design until it shrinks
  a convention mandates a comment on every declaration => the one sentence a caller
    needs, plus what static analysis and IDE tooling require, JSDoc with type
    signatures under @ts-check and the like
  in doubt, leave it out
}

Edit {
  an invariant worth enforcing => write the test that checks it
  that test cannot land in this change => a TODO with an owner or ticket
  an edit leaves a nearby comment restating its neighbors or contradicting the code =>
    remove it in the same edit
  a comment holding an invariant or a contract sits inside the change's scope =>
    remove it, moving what it holds into a type, a test, or a name wherever one of
    them can check it
}
```
