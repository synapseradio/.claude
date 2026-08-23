# Writing comments

This applies to every comment in source code.

Six kinds of comment exist. Why: rationale, with alternatives rejected. Contract: a unit's promise to its caller, worded so the caller trusts the interface unread. Invariant: what must hold where a type cannot say it, and a test does not exist. Warning: the hazard a reader cannot see, naming what breaks on contact. Anchor: the domain fact the code answers to, citing its protocol, spec, or regulation. Map: orientation otherwise rebuilt by hand, a state layout or the key idea behind a non-obvious algorithm.

Contract and Invariant comments are a code smell. Contracts and invariants belong in at least two of: tests, types, names, documentation. Do not write comments to describe contracts or invariants unless there is no name for what is being commented, no way to test against it, no type that could describe it, and there is documentation that does, or should, exist to replace the need.

Before writing a comment, route the knowledge to tests, types, names, documentation. When it does not outlive the code beside it (today's change, the bug, the date), put it in the commit, the PR, or the ticket, and write no comment. When it fits a name, a type, a test, or a doc, put it there, and write no comment. When it states what the code does, improve the code until the would-be comment falls away, and write no comment. When it fits one of the six kinds, write that kind, and otherwise write nothing. Bind the comment to one point, on its referent.

Word it to hold now, for as long as the code stands: no date, no version, no "was", "will", "for now", "currently", "still", or "soon". For a banner marking a moment, ask first. Every external referent carries an http(s) link, never a disk path or a line number unless the user asks. When an invariant is worth enforcing, write the test that checks it and a comment saying why it holds, and when the test cannot land in this change, leave a TODO with an owner or ticket and ask the user to add it. When knowledge spans more than one file, put it in docs and point the comment there. Draft the interface comment before the body, and when you cannot keep it short, fix the design until it shrinks.

When an edit brings a nearby comment within reach, hold it to this rule, and remove one that restates its neighbors or contradicts the code in the same edit. When a convention mandates a comment on every declaration, write the one sentence a caller needs, plus what static analysis and IDE tooling require: JSDoc with type signatures under @ts-check, and the like.

When in doubt, leave it out. When it is right, keep it concise.
