<rule name="writing-comments">

<applies_when>You are writing a comment in source code.</applies_when>

<optimize_for>
a comment written only after the code itself, a name, a type, a test, and a document have each failed to carry what needs saying.
<why_it_matters>Nothing checks the content of a comment, so an invariant kept there tends to drift from the code beside it, while a type, a test, or a name holds it in step. A contract stated in at least two of tests, types, names, and documentation can be read from either one. A comment worded to a moment goes stale while the code stands.</why_it_matters>
</optimize_for>

<decide name="route">

Route each piece of knowledge before writing a comment.

- When it does not outlive the code beside it, today's change, the bug, the date, it goes to the commit, the PR, or the ticket, and no comment.
- When it fits a name, a type, a test, or a doc, put it there, and no comment.
- When it states what the code does, improve the code until the would-be comment falls away.
- When it states an invariant, it goes to the type, the test, or the name that carries it, and no comment.
- When it explains why an invariant holds, ask the user, and write nothing until they approve.
- When it warns of a hazard, it goes to the test that fails on contact with it, and no comment.
- When it spans more than one file, it goes to docs, with the comment pointing there.
- When it is a promise a type or a static analysis tool the project runs can make, no Contract comment.
- When it is a promise documentation that does or should exist replaces, no Contract comment.
- When it names a person or group to consult whom the user never named, no Consult comment.
- When it fits one of the comment kinds, write that kind, bound to one point, on its referent.
- Otherwise, write nothing.

</decide>

<define name="comment kinds">
A Why comment is rationale. A Contract comment is a unit's promise to its caller, worded for a caller who reads the interface and nothing else. A Consult comment is the person or group the user names to talk to before this code changes, in a codebase with several owners. An Anchor comment is the domain fact the code answers to, citing its protocol, spec, or regulation. A Map comment is orientation otherwise rebuilt by hand, a state layout or the key idea behind a non-obvious algorithm.
</define>

<do name="write">
Draft the interface comment before the body. Word it to hold for as long as the code stands: no date, no version, no "was", "will", "for now", "currently", "still", or "soon". Every external referent carries an http or https link, and where the user asks for a disk path or a line number, give that. Where a banner would mark a moment, ask first. Where the comment will not stay short, fix the design until it shrinks. Where a convention mandates a comment on every declaration, write the one sentence a caller needs, plus what static analysis and IDE tooling require, JSDoc with type signatures under @ts-check and the like. In doubt, leave it out.
</do>

<decide name="edit">
Where an invariant is worth enforcing, write the test that checks it. Where that test cannot land in this change, leave a TODO with an owner or ticket. Where an edit leaves a nearby comment restating its neighbors or contradicting the code, remove it in the same edit. Where a comment holding an invariant or a contract sits inside the change's scope, remove it, moving what it holds into a type, a test, or a name wherever one of them can check it.
</decide>

</rule>
