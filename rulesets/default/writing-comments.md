<!-- rule: writing-comments -->

## writing-comments

For every comment in source code, whether you write it or an edit of yours lands beside it, optimize for a comment written only after the code itself, a name, a type, a test, and a document have each failed to carry what needs saying.

### Where each piece of knowledge goes

Decide first whether a comment exists and which kind it takes, by routing each piece of knowledge. Take the first arm that fits.

- When it does not outlive the code beside it, today's change for one, it goes to the commit, the PR, or the ticket, and no comment.
- When it recounts a path the code left behind, it goes to the commit or the PR, and no comment.
- When it is a platform or library behavior the code rests on, and a documentation page backs it, write a Why comment linking that page.
- When it explains why a test asserts what it asserts, write a Why comment in the test, linking the documentation page for each browser, framework, or library behavior it assumes.
- When it fits a name, a type, a test, or a doc, put it there, and no comment.
- When it states what the code does, improve the code until the would-be comment falls away.
- When it states an invariant, it goes to the type, the test, or the name that carries it, and no comment.
- When it explains why an invariant holds, ask the user, and write nothing until they approve.
- When it warns of a hazard that no test can exercise and no document can carry, write a Hazard comment. Afterward, tell the user in conversation why no test and no document could carry it. Keep that explanation out of every artifact.
- When it warns of a hazard no test can exercise, it goes to docs, and no comment.
- When it warns of a hazard, it goes to the test that fails on contact with it, and no comment.
- When it spans more than one file, it goes to docs, and no comment.
- When it asks the reader to reach a team the user never named, write no Consult comment.
- When it fits a Why, Consult, Anchor, or Map comment, four of the kinds defined below, write that kind. Keep it to one point. Attach it to its referent, the code the comment describes.
- Otherwise, write nothing.

### Carrying an invariant

Where no type or name can carry an invariant, write the test that checks it. Where that test cannot land in this change, write a TODO naming the test by the description it will carry, plus an owner or ticket, leaving the assertion to the test. Where no owner or ticket is known, ask the user before writing the TODO.

### The comment kinds

A Why comment is rationale that names each platform or library behavior its referent rests on and links the documentation page that backs it. A framework's or library's page is the one for the version the local manifest and lockfile resolve, package.json for one. A Consult comment asks whoever changes an area to reach a named team first, on the pattern of "please reach out to our team before making changes in this area". An Anchor comment is the domain fact the code answers to, citing its protocol, spec, or regulation. A Map comment lays out a structure inside its referent that a reader would otherwise rebuild from the code before changing it, a state layout for one, where no type can carry that structure. A Hazard comment warns of a break in its referent that no test can exercise and no document can carry. An external referent is anything a comment cites outside the file it sits in.

### Writing the comment

Draft the declaration's comment, the one a caller reads, before writing the body. Write it in short declaratives with the subject first, under the rule on prose. Write for an engineer competent in the language and the field. Count the language and the common surface of a framework as known to that reader, and cut what restates it. Keep a comment that explains a subtle or less common framework or library feature, a React portal for one. Word the comment to the present state of the code, with no date, no version, no word that marks a moment, "currently" for one, and no account of a path the code left behind. Keep a mechanical verb the code verifiably performs as the subject's verb. Set a blank line before and after a comment block. Where a sentence was reworded to dodge an apostrophe, a quote, or an escape, write the correct sentence first, then the quotes that carry it. Where a banner would mark a moment, ask first.

Give every external referent an http or https link. Give a document in the same repository its forge URL, the address at which the repository host serves it. Where the user asks for a disk path or a line number, give that. Where a test file covers the referent, a comment may link that file. Where a Why comment would rest on a behavior with no page to link, write no comment. Where no test shows that behavior, write one. Before linking a framework or library page, read the resolved version from the local manifest or lockfile, and link the page for that version. Where the linked page documents another version than the lockfile resolves, replace the link with the resolved version's page.

Let every sentence in a comment state the one point its referent cannot carry, or link that point's source. Cut every other sentence, moving what it carried to a test, a document, or a link. Where the point will not fit the words a caller needs in order to act, stop writing and fix what forced it: rename until the name carries it, split the function until each part explains itself, or move the explanation to a document and leave the link. Treat a comment that outruns the code it sits on as a document filed in the wrong place: move it and leave the link. Cut a comment sentence that still reads dense after one rewrite, moving what it carried to a test, a document, or a link. Where a convention mandates a comment on every declaration, write the one sentence a caller needs, plus what static analysis and IDE tooling require, JSDoc with type signatures under @ts-check for one. In doubt, leave it out.

Never write a comment saying that a condition always holds, never occurs, or must be kept. Never write a comment whose only content asserts the current behavior of the source. Describe code outside the file a comment sits in only in a test's Why comment, naming the behavior under test the assertion rests on. Never restate in a comment what a linked page, test, or file holds, beyond naming the behavior the code rests on. Never link a pull request or a commit from a comment.

### Editing beside a comment

Where an edit leaves a nearby comment restating its neighbors, contradicting the code, or recounting a path the code left behind, remove it in the same edit. Where a comment holding an invariant sits inside the change's scope, remove it, moving what it holds into a type, a test, or a name wherever one of them can check it.
