<!-- rule: comments -->

## comments

For every comment in source code that you write or land an edit beside, optimize for a comment written only after the code, a name, a type, a test, and a document each failed to carry what needs saying.

Read every comment with healthy skepticism, most of all one claiming an invariant or a guarantee of behavior.

### Where each piece of knowledge goes

Route each piece of knowledge first, deciding whether a comment exists and its kind. Take the first arm that fits.

- When it lasts no longer than the code beside it, today's change for one, it goes to the commit, the PR, or the ticket.
- When it recounts a path the code left behind, it goes to the commit or the PR.
- When it is a platform or library behavior the code rests on or is limited by, backed by a documentation page, write a Why comment linking that page.
- When it explains why a test asserts what it does, write a Why comment in the test, linking the documentation page for each browser, framework, or library behavior it assumes.
- When it says what an exported declaration or a file is for, write a Summary comment on the declaration or at the file's head.
- When it fits a name, a type, a test, or a doc, put it there.
- When it states what the code does, improve the code until the would-be comment falls away.
- When it states an invariant, it goes to the type, the test, or the name that carries it.
- When it explains why an invariant holds, ask the user, and write only on their approval.
- When it warns of a hazard no test can exercise and no documentation page holds, write a Hazard comment. Then tell the user in conversation why no test can exercise it and where you looked for a page. Keep that explanation out of every artifact.
- When it warns of a hazard no test can exercise, it goes to docs.
- When it warns of a hazard, it goes to the test that fails on contact with it.
- When it spans more than one file, it goes to docs.
- When it asks the reader to reach a team outside those the user named, keep it out of every Consult comment.
- When it fits a Why, Consult, Anchor, or Map comment, as defined below, write that kind. Keep it to one point. Attach it to its referent, the code it describes.
- Otherwise, leave it unwritten.

Keep knowledge an arm sends elsewhere out of every comment.

### Carrying an invariant

Where no type or name can carry an invariant, write the test that checks it. Where that test must land in a later change, write a TODO naming the test by the description it will carry, plus an owner or ticket, leaving the assertion to the test. Where neither owner nor ticket is known, ask the user before writing the TODO.

### The comment kinds

A Why comment is rationale naming each platform or library behavior its referent rests on or is limited by, linking the documentation page that backs it.

A Consult comment asks whoever changes an area to reach a named team first, as in "please reach out to our team before making changes in this area".

An Anchor comment is the domain fact the code answers to, citing its protocol, spec, or regulation.

A Map comment lays out a structure in its referent, a state layout for one, that no type can carry and a reader would otherwise rebuild from the code before changing it.

A Hazard comment warns of a break in its referent that no test can exercise and no documentation page holds.

A Summary comment is one sentence on an exported declaration or at a file's head, saying what it is for.

An external referent is anything a comment cites outside its own file.

### Writing the comment

Draft the declaration's comment, the one a caller reads, before the body. Write it in short subject-first declaratives. Make the subject's verb a mechanical one the code verifiably performs.

Write for a developer competent in the language and in software engineering, and new to the code's problem domain. Count the language and a framework's common surface as known to that reader, and cut what restates them. Keep a comment explaining a subtle or uncommon framework or library feature, a React portal for one. Give the reader the domain familiarity the code assumes. Where a comment would explain an engineering choice, state the domain fact or problem the choice answers.

Word the comment to the code's present state, keeping out every date, version, and word marking a moment, "currently" for one. Ask before writing a banner that marks a moment.

Set a blank line before a comment block. Where a sentence was reworded to dodge an apostrophe, a quote, or an escape, write the correct sentence first, then the quotes that carry it.

Give every external referent an http or https link. Give a document in the same repository its forge URL, the address the repository host serves it at. Where the user asks for a disk path or a line number, give that. A comment may link a test file that covers its referent. Count an issue on a project's public tracker as a page to link. Keep every link to a pull request or a commit out of a comment.

Where a Why comment would rest on a behavior with no page to link, leave the comment unwritten. Where a test can show that behavior and none exists, write one. Where no test can show it, route it as a hazard.

Before linking a framework or library page, read the resolved version from the local manifest, package.json for one, or the lockfile, and link that version's page. Where a linked page documents a version other than the lockfile resolves, replace it with the resolved version's page.

Let each sentence in a comment state the one point its referent cannot carry, or link that point's source. Cut every other sentence, and every one still dense after one rewrite, moving what it carried to a test, a document, or a link. In doubt, leave it out.

Where the point takes more words than a caller needs to act, stop and fix what forced it: rename until the name carries it, split the function until each part explains itself, or move the explanation to a document and leave the link. Treat a comment longer than the code it sits on as a misfiled document: move it and leave the link.

Where a convention mandates a comment on every declaration, write the one sentence a caller needs, plus what static analysis and IDE tooling require, JSDoc with type signatures under @ts-check for one.

Keep out of every comment any claim that a condition always holds, never occurs, or must be kept. Reserve a comment asserting only the source's current behavior for a Summary comment.

Describe code outside a comment's own file only in a test's Why comment, naming the behavior under test the assertion rests on. Keep every restatement of a linked page, test, or file out of a comment, beyond naming the behavior the code rests on.

### Editing beside a comment

Where an edit leaves a nearby comment restating its neighbors, contradicting the code, or recounting a path the code left behind, remove it in that edit. Where a comment holding an invariant sits in the change's scope, remove it, moving what it holds into a type, a test, or a name wherever one can check it.
