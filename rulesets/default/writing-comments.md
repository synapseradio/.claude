<!-- rule: writing-comments -->

## writing-comments

For every comment in source code, whether you write it or an edit of yours lands beside it, optimize for a comment written only after the code itself, a name, a type, a test, and a document have each failed to carry what needs saying.

### Where each piece of knowledge goes

Decide first whether a comment exists and which kind it takes, by routing each piece of knowledge.

- When it does not outlive the code beside it, today's change for one, it goes to the commit, the PR, or the ticket, and no comment.
- When it recounts a path the code left behind, it goes to the commit or the PR, and no comment.
- When it fits a name, a type, a test, or a doc, put it there, and no comment.
- When it states what the code does, improve the code until the would-be comment falls away.
- When it states an invariant, it goes to the type, the test, or the name that carries it, and no comment.
- When it explains why an invariant holds, ask the user, and write nothing until they approve.
- When it warns of a hazard, it goes to the test that fails on contact with it, and no comment.
- When it spans more than one file, it goes to docs, with the comment pointing there.
- When it names a team to reach whom the user never named, no Consult comment.
- When it fits one of the comment kinds, write that kind, bound to one point, on its referent.
- Otherwise, write nothing.

### The comment kinds

A Why comment is rationale, linking the documentation of every platform or library behavior it rests on, at the version the lockfile resolves. A Consult comment asks whoever changes an area to reach a named team first, on the pattern of "please reach out to our team before making changes in this area". An Anchor comment is the domain fact the code answers to, citing its protocol, spec, or regulation. A Map comment is orientation otherwise rebuilt by hand, a state layout for one. An external referent is anything outside the file the comment sits in.

### Writing the comment

Draft the comment on the declaration, the one a caller reads, before the body. Write it in short declaratives with the subject first, under the rule on prose. Let every sentence in a comment state the one point its referent cannot carry, or link that point's source. Cut every other sentence, moving what it carried to a test, a document, or a link. Where the point will not fit the words a caller needs in order to act, stop writing and fix what forced it: rename until the name carries it, split the function until each part explains itself, or move the explanation to a document and leave the link. Treat a comment that outruns the code it sits on as a document filed in the wrong place: move it and leave the link. Cut a comment sentence that still reads dense after one rewrite, moving what it carried to a test, a document, or a link. Word the comment to the present state of the code, with no date, no version, no word that marks a moment, "currently" for one, and no account of a path the code left behind. Set a blank line before and after a comment block. Give every external referent an http or https link. Give a document in the same repository its forge URL, the address at which the repository host serves it. Where the user asks for a disk path or a line number, give that. Where a Why comment would rest on a behavior with no page to link, write no Why comment, and find the source or the test that shows the behavior. Where the linked page documents another version than the lockfile resolves, replace the link with the resolved version's page. Where a banner would mark a moment, ask first. Keep a mechanical verb the code verifiably performs as the subject's verb. Where a sentence was reworded to dodge an apostrophe, a quote, or an escape, write the correct sentence first, then the quotes that carry it. Where a convention mandates a comment on every declaration, write the one sentence a caller needs, plus what static analysis and IDE tooling require, JSDoc with type signatures under @ts-check for one. In doubt, leave it out.

Never write a comment saying that a condition always holds, never occurs, or must be kept. Explain why an invariant holds only in a comment the user approved after you asked. Write a Consult comment only on the user's naming of the team.

### Editing beside a comment

Where an invariant is worth enforcing, write the test that checks it. Where that test cannot land in this change, write a TODO naming the test and an owner or ticket, leaving what the test will state to the test. Where no owner or ticket is known, ask the user before writing the TODO. Where an edit leaves a nearby comment restating its neighbors, contradicting the code, or recounting a path the code left behind, remove it in the same edit. Where a comment holding an invariant sits inside the change's scope, remove it, moving what it holds into a type, a test, or a name wherever one of them can check it.
