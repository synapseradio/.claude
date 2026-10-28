<!-- rule: comments -->

## comments

For every comment in source code that you write or land an edit beside, optimize for a comment written only after the code, a name, a type, a test, and a document each failed to carry what needs saying.

Read every comment with healthy skepticism, most of all one claiming an invariant or a guarantee of behavior.

### Where each piece of knowledge goes

Route each piece of knowledge first, deciding whether a comment exists and its kind. Take the first arm that fits.

```haskell
home k
  | concerns a change rather than the code as it stands,
    today's change or a path the code left behind
      = the commit, the PR, or the ticket
  | explains why an invariant holds
      = ask the user, and write only on their approval
  | is a platform or library behavior the code rests on or is limited by,
    backed by a documentation page
      = write a Why comment linking that page
  | explains why a test asserts what it does
      = write a Why comment in the test, linking the documentation page
        for each browser, framework, or library behavior it assumes
  | says what an exported declaration or a file is for
      = write a Summary comment on the declaration or at the file's head
  | the code itself, a name, a type, or a test can state it whole
      = the first of those that can, the code by improving it
        until the would-be comment falls away
  | spans more than one file, or a documentation page already holds it whole
      = docs
  | fits a comment kind defined below
      = write that kind; keep it to one point;
        attach it to its referent, the code it describes
  | otherwise = leave it unwritten
```

A carrier states knowledge whole where a reader of that carrier alone learns it. Hold a type, a test, or a name as the only home of an invariant. Keep knowledge an arm sends elsewhere out of every comment. After writing a Hazard comment, tell the user in conversation why no test can exercise it and where you looked for a page, keeping that explanation out of every artifact.

### Carrying an invariant

An invariant's test must land in a later change ? write a TODO naming the test by the description it will carry, plus an owner or ticket, leaving the assertion to the test.
Neither owner nor ticket is known ? ask the user before writing the TODO.

### The comment kinds

A Why comment is rationale naming each platform or library behavior its referent rests on or is limited by, linking the documentation page that backs it.

A Consult comment asks whoever changes an area to reach a named team first, as in "please reach out to our team before making changes in this area". Name in a Consult comment only a team the user named.

An Anchor comment is the domain fact the code answers to, citing its protocol, spec, or regulation.

A Map comment lays out a structure in its referent, a state layout for one, that no type can carry and a reader would otherwise rebuild from the code before changing it.

A Hazard comment warns of a break in its referent that no test can exercise and no documentation page holds.

A Summary comment is one sentence on an exported declaration or at a file's head, saying what it is for.

An external referent is anything a comment cites outside its own file.

### Writing the comment

Draft the declaration's comment, the one a caller reads, before the body. Write it in short subject-first declaratives. Make the subject's verb a mechanical one the code verifiably performs.

Write for a developer competent in the language and in software engineering, and new to the code's problem domain. Count the language and a framework's common surface as known to that reader, and cut what restates them. Keep a comment explaining a subtle or uncommon framework or library feature, a React portal for one. Give the reader the domain familiarity the code assumes.
A comment would explain an engineering choice ? state the domain fact or problem the choice answers.

Word the comment to the code's present state, keeping out every date, version, and word marking a moment, "currently" for one. Ask before writing a banner that marks a moment.

Set a blank line before a comment block.
A sentence was reworded to dodge an apostrophe, a quote, or an escape ? write the correct sentence first, then the quotes that carry it.

Give every external referent an http or https link. Give a document in the same repository its forge URL, the address the repository host serves it at.
The user asks for a disk path or a line number ? give that.
A comment may link a test file that covers its referent. Count an issue on a project's public tracker as a page to link. Keep every link to a pull request or a commit out of a comment.

A Why comment would rest on a behavior with no page to link ? route that behavior as a hazard in place of the comment.

Link a framework or library page at the version the local manifest, package.json for one, or the lockfile resolves, and replace a linked page for any other version with that one.

Let each sentence in a comment state the one point its referent cannot carry, or link that point's source. Cut every other sentence, and every one still dense after one rewrite, moving what it carried to a test, a document, or a link. In doubt, leave it out.

The point takes more words than a caller needs to act ? stop and fix what forced it, by renaming until the name carries it, splitting the function until each part explains itself, or moving the explanation to a document and leaving the link.
Treat a comment longer than the code it sits on as a misfiled document: move it and leave the link.

A convention mandates a comment on every declaration ? write the one sentence a caller needs, plus what static analysis and IDE tooling require, JSDoc with type signatures under @ts-check for one.

Describe code outside a comment's own file only in a test's Why comment, naming the behavior under test the assertion rests on. Keep every restatement of a linked page, test, or file out of a comment, beyond naming the behavior the code rests on.

### Editing beside a comment

An edit leaves a nearby comment restating its neighbors, contradicting the code, or recounting a path the code left behind ? remove it in that edit.
A comment holding an invariant sits in the change's scope ? move what it holds to its home and remove the comment.
