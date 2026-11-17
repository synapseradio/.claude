## comments

For every comment in source code you write or land an edit beside, optimize for a comment written only after the code and a name and a type and a test and a doc each failed to carry its point.

- referent: the code a comment describes
- page: a documentation page, an issue on a public tracker included
- hold whole: a reader of that carrier alone learns it
- Why: rationale naming each platform or library behavior the referent rests on or is limited by, linking the page that backs it
- Consult: asks whoever changes the area to reach a team the user named first, as in "please reach out to our team before making changes in this area"
- Anchor: the domain fact the code answers to, citing the standard that states it
- Map: a structure in the referent no type carries, such as a state layout, that a reader would otherwise rebuild before changing it
- Hazard: a break in the referent no test can exercise and no page holds
- Summary: one sentence on an exported declaration or at a file's head, saying what it is for

Read every comment skeptically, most of all one claiming an invariant or a guarantee.

Route each piece of knowledge before writing, and keep what a line sends elsewhere out of comments.

home k
  | about a change or a path the code left rather than the code as it stands = the commit, PR, or ticket
  | why an invariant holds = ask the user -> write only on approval
  | a platform or library behavior the code rests on or is limited by, with a page = Why linking it
  | a platform or library behavior with no page = Hazard
  | what an export or a file is for = Summary
  | one of code > a name > a type > a test can hold it whole = the first that can, improving code until the comment falls away
  | spans files, or a page holds it whole = docs
  | fits a kind = that kind, one point, attached to its referent
  | otherwise = no comment

hazard
  | written = tell the user in conversation, outside every artifact, why no test can exercise it and where you looked for a page

Keep each invariant only in a type, a test, or a name.

invariant
  | its home lands in a later change with owner and ticket both unknown = ask the user first
  | its home lands in a later change = write a TODO naming that home by its description plus an owner or ticket, leaving the invariant to it
  | a comment holding one sits in the change's scope = move it to its home -> remove the comment

edit
  | it leaves a nearby comment restating its neighbors, contradicting the code, or recounting a path left behind = remove that comment in that edit

Draft a declaration's caller-facing comment before its body, in short subject-first declaratives whose verbs the code mechanically, verifiably performs.
Write for a developer new to the domain and fluent in the language, software engineering, and a framework's common surface.
Cut what they know, supply the domain the code assumes, and keep a subtle or uncommon framework or library feature such as a React portal.
Word it to the present state with no date, version, or moment word like "currently".
Set a blank line before a comment block.

comment
  | it would explain an engineering choice = state the domain fact or problem it answers
  | a banner would mark a moment = ask first
  | a sentence was reworded to dodge quoting or escaping = write the correct sentence -> add the quoting or escaping that carries it

Link everything a comment cites outside its file by http or https: a same-repo doc by its URL on the repository host, a framework or library page at the version the manifest or lockfile resolves, replacing any other version's.
A comment may link a test file covering its referent, with every PR and commit link kept out.

link
  | the user asks for a disk path or line number = give that

Let each sentence state the one point its referent can't carry, or link that point's source.
Cut the rest and move any sentence still dense after one rewrite to a test, doc, or link.

length
  | a convention demands a comment per declaration = write the one sentence a caller needs plus what static analysis and IDE tooling require, such as JSDoc types under @ts-check
  | the point needs more words than a caller needs to act = fix what forced it: rename until the name carries it, split the function until each part explains itself, or move it to a doc -> link it
  | a comment outruns its code = move it to a doc -> link it
  | in doubt = leave it out

Describe in a comment only code in the comment's own file.
Name of a linked page, test, or file only the behavior relied on.
