<!-- rule: comments -->

## comments

For every comment in source code you write or land an edit beside, optimize for a comment written only after the code, a name, a type, a test, and a doc each failed to carry its point.

- referent: the code a comment describes.
- page: a documentation page, an issue on a public tracker included.
- hold whole: a reader of that carrier alone learns it.
- Why: rationale naming each platform or library behavior the referent rests on or is limited by, linking the page that backs it.
- Consult: asks whoever changes the area to reach a team the user named first, as in "please reach out to our team before making changes in this area".
- Anchor: the domain fact the code answers to, citing its protocol, spec, or regulation.
- Map: a structure in the referent no type carries, a state layout for one, that a reader would otherwise rebuild before changing it.
- Hazard: a break in the referent no test can exercise and no page holds.
- Summary: one sentence on an exported declaration or at a file's head, saying what it is for.

Read every comment skeptically, most of all one claiming an invariant or a guarantee.

Route each piece of knowledge before writing, taking the first arm that fits, and keep what an arm sends elsewhere out of comments.

home k
  | about a change or a path the code left, not the code as it stands = the commit, PR, or ticket
  | why an invariant holds = ask the user -> write only on approval
  | a platform or library behavior the code rests on or is limited by, with a page = Why linking it
  | why a test asserts what it does = Why in the test, linking a page per browser, framework, or library behavior it assumes
  | what an export or a file is for = Summary
  | code, a name, a type, or a test can hold it whole = the first that can, improving code until the comment falls away
  | spans files, or a page holds it whole = docs
  | fits a kind = that kind, one point, attached to its referent
  | otherwise = no comment

A behavior with no page ? route it as a hazard, never a Why.
Hazard written ? tell the user in conversation, never in an artifact, why no test can exercise it and where you looked for a page.

Keep each invariant only in a type, a test, or a name.
Its test lands in a later change ? write a TODO naming the test by its description, plus an owner or ticket, leaving the assertion to the test.
Owner and ticket both unknown ? ask the user first.
A comment holding an invariant sits in the change's scope ? move the invariant to its home -> remove the comment.
An edit leaves a nearby comment restating its neighbors, contradicting the code, or recounting a path left behind ? remove it in that edit.

Draft a declaration's caller-facing comment before its body, in short subject-first declaratives whose verbs the code mechanically, verifiably performs.
Write for a developer fluent in the language, software engineering, and a framework's common surface, and new to the domain: cut what they know, keep a subtle or uncommon framework or library feature, a React portal for one, and supply the domain the code assumes.
A comment would explain an engineering choice ? state the domain fact or problem it answers.
Word it to the present state, with no date, version, or moment word like "currently".
A banner would mark a moment ? ask first.
Set a blank line before a comment block.
A sentence was reworded to dodge an apostrophe, quote, or escape ? write the correct sentence -> add the quoting or escaping that carries it.

Link everything a comment cites outside its file by http or https: a same-repo doc by its URL on the repository host, a framework or library page at the version the manifest or lockfile resolves, replacing any other version's.
The user asks for a disk path or line number ? give that.
A comment may link a test file covering its referent, and never a PR or commit.

Let each sentence state the one point its referent can't carry, or link that point's source; cut the rest, and any still dense after one rewrite, moving it to a test, doc, or link.
In doubt ? leave it out.
The point needs more words than a caller needs to act ? fix what forced it: rename until the name carries it, split the function until each part explains itself, or move it to a doc -> link it.
A comment outruns its code ? move it to a doc -> link it.
A convention demands a comment per declaration ? write the one sentence a caller needs plus what static analysis and IDE tooling require, JSDoc types under @ts-check for one.
Describe code outside the comment's file only in a test's Why, naming the behavior under test the assertion rests on.
Restate no linked page, test, or file beyond naming the behavior relied on.
