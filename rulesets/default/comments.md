<!-- rule: comments -->

## comments

For every comment in source code, whether you write it or an edit lands beside it, optimize for a comment written only after the code itself, a name, a type, a test, and a document have each failed to carry what needs saying.

Always read comments with a healthy degree of skepticism, especially where they are writing supposed invariants or guarantees of behavior.

### Where each piece of knowledge goes

Decide first whether a comment exists and which kind it takes, by routing each piece of knowledge. Take the first arm that fits.

- When it lasts at most as long as the code beside it, today's change for one, it goes to the commit, the PR, or the ticket, in place of a comment.
- When it recounts a path the code left behind, it goes to the commit or the PR, in place of a comment.
- When it is a platform or library behavior the code rests on or is limited by, and a documentation page backs it, write a Why comment linking that page.
- When it explains why a test asserts what it asserts, write a Why comment in the test, linking the documentation page for each browser, framework, or library behavior it assumes.
- When it says what an exported declaration or a file is for, write a Summary comment on that declaration or at the head of that file.
- When it fits a name, a type, a test, or a doc, put it there, in place of a comment.
- When it states what the code does, improve the code until the would-be comment falls away.
- When it states an invariant, it goes to the type, the test, or the name that carries it, in place of a comment.
- When it explains why an invariant holds, ask the user, and write only after they approve.
- When it warns of a hazard beyond what any test can exercise and absent from every documentation page, write a Hazard comment. Afterward, tell the user in conversation why it lies beyond what any test can exercise and where you looked for a page. Keep that explanation out of every artifact.
- When it warns of a hazard beyond what any test can exercise, it goes to docs, in place of a comment.
- When it warns of a hazard, it goes to the test that fails on contact with it, in place of a comment.
- When it spans more than one file, it goes to docs, in place of a comment.
- When it asks the reader to reach a team outside the teams the user named, keep it out of every Consult comment.
- When it fits a Why, Consult, Anchor, or Map comment, four of the kinds defined below, write that kind. Keep it to one point. Attach it to its referent, the code the comment describes.
- Otherwise, leave it unwritten.

### Carrying an invariant

Where an invariant lies beyond what any type or name can carry, write the test that checks it. Where that test must land in a later change, write a TODO naming the test by the description it will carry, plus an owner or ticket, leaving the assertion to the test. Where both the owner and the ticket are unknown, ask the user before writing the TODO.

### The comment kinds

A Why comment is rationale that names each platform or library behavior its referent rests on or is limited by and links the documentation page that backs it.

A Consult comment asks whoever changes an area to reach a named team first, on the pattern of "please reach out to our team before making changes in this area".

An Anchor comment is the domain fact the code answers to, citing its protocol, spec, or regulation.

A Map comment lays out a structure inside its referent that a reader would otherwise rebuild from the code before changing it, a state layout for one, where that structure lies beyond what any type can carry.

A Hazard comment warns of a break in its referent beyond what any test can exercise and absent from every documentation page.

A Summary comment is one sentence on an exported declaration, or at the head of a file, saying what that declaration or file is for.

An external referent is anything a comment cites outside the file it sits in.

### Writing the comment

Draft the declaration's comment, the one a caller reads, before writing the body. Write it in short declaratives with the subject first. Keep a mechanical verb the code verifiably performs as the subject's verb.

Write for a software developer competent in the language and in software engineering, and new to the problem domain the code serves. Count the language and the common surface of a framework as known to that reader, and cut what restates it. Keep a comment that explains a subtle or less common framework or library feature, a React portal for one. Give the reader the domain familiarity the code assumes. Where a comment would explain an engineering choice, state the domain fact or the problem the choice answers.

Word the comment to the present state of the code, keeping out every date, every version, and every word that marks a moment, "currently" for one. Where a banner would mark a moment, ask first.

Set a blank line before a comment block. Where a sentence was reworded to dodge an apostrophe, a quote, or an escape, write the correct sentence first, then the quotes that carry it.

Give every external referent an http or https link. Give a document in the same repository its forge URL, the address at which the repository host serves it. Where the user asks for a disk path or a line number, give that. Where a test file covers the referent, a comment may link that file. Count an issue on a project's public tracker as a page to link. Keep every link to a pull request or a commit out of a comment.

Where a Why comment would rest on a behavior that lacks a page to link, leave the Why comment unwritten. Where a test can show that behavior and that test is missing, write one. Where it lies beyond what any test can show, route it as a hazard.

Before linking a framework or library page, read the resolved version from the local manifest, package.json for one, or the lockfile, and link the page for that version. Where the linked page documents another version than the lockfile resolves, replace the link with the resolved version's page.

Let every sentence in a comment state the one point beyond what its referent can carry, or link that point's source. Cut every other sentence, and every sentence that still reads dense after one rewrite, moving what it carried to a test, a document, or a link. In doubt, leave it out.

Where the point takes more words than a caller needs in order to act, stop writing and fix what forced it: rename until the name carries it, split the function until each part explains itself, or move the explanation to a document and leave the link. Treat a comment that outruns the code it sits on as a document filed in the wrong place: move it and leave the link.

Where a convention mandates a comment on every declaration, write the one sentence a caller needs, plus what static analysis and IDE tooling require, JSDoc with type signatures under @ts-check for one.

Keep out of every comment any claim that a condition always holds, never occurs, or must be kept. Reserve a comment whose only content asserts the current behavior of the source for a Summary comment.

Describe code outside the file a comment sits in only in a test's Why comment, naming the behavior under test the assertion rests on. Keep every restatement of what a linked page, test, or file holds out of a comment, beyond naming the behavior the code rests on.

### Editing beside a comment

Where an edit leaves a nearby comment restating its neighbors, contradicting the code, or recounting a path the code left behind, remove it in the same edit. Where a comment holding an invariant sits inside the change's scope, remove it, moving what it holds into a type, a test, or a name wherever one of them can check it.
