<!-- rule: comments -->
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

<!-- rule: data-modeling -->
## data-modeling

For every type you design or change in code or in reasoning about it, an interface signature or an error channel included, optimize for a type that admits only legal states and is bought only where it deletes a "should never happen" branch.

- panic: the runtime failure on a state that should never happen

Model with product types, sum types, and exhaustive matching.
Count a newtype wrapper as ergonomics, with every state it wraps still admitted.

model
  | it reaches past them, such as to GADTs = stop and check whether a value check crept back in

### The runtime check

Treat every runtime check for a state that should never happen as a modeling decision.
Test a state only where the type can represent it.

guard
  | a "should never happen" branch outlasts the moves = strengthen the type until the branch disappears, at the first rung the gain pays for
  | a runtime check, assertion, or throw guards a state that should never happen = ask each move's test question below -> apply each move whose answer is yes -> model the state out or knowingly accept the panic

The rungs: a precise type > an abstract type with a smart constructor (validated inside, exposing only invariant-preserving methods, its method set closed) > a check guarding the invariant in place of the declined type.

### The moves

Each move carries a step, an example, and a test question.

Model the positive space.
List the legal states, one constructor per state.
For a user reachable by email or phone or both, write a constructor per case, where two optional fields also admit a user with both empty.
Test: can you list the legal states as cases?

Choose the representation for the code at hand.
Pick whichever serves the code reading it, converting at boundaries.
For a time range ordered by construction, use a start time plus a duration of zero or more, where two raw timestamps need a check.
Test: would another representation let you delete this check?

Let types propagate obligations.
Link producers and consumers through the type definition, so a new case makes exhaustive matching report every consumer site.
A fourth contact kind added to the union fails every match that lacks it.
Test: could a new case leave a consumer the compiler stays silent about?

Buy precision where it deletes a panic.
Strengthen the type at the site of a "should never happen" throw, and keep the simplest representation at every other site.
An email address stays a plain string until code inspects its structure.
Test: does this precision delete a panic?

Move obligations to whoever can discharge them.
Use a required parameter over an optional value, and parse loose input into a precise type once at a boundary, then pass it inward.
A non-empty list gets parsed at the API edge, where a check returning only a verdict makes every downstream site check again.
Test: can the caller handle this failure where this code cannot?

<!-- rule: debugging -->
## debugging

For every problem you debug, optimize for a repair that follows a hypothesis a test decided.

State the active hypothesis before changing anything -> let the cheapest test decide it.

cause
  | your measurement runs against the user's root cause = voice it once -> investigate theirs either way
  | the user identifies a root cause = investigate it first, holding each alternative until ruled out

Name the cause only once a test decided it, whoever proposed it.

<!-- rule: repairing -->
## repairing

For every named defect you fix in an artifact, optimize for a repair that clears the defect and keeps the unit's job.

- unit's job: evidence (a fact it carries) or instruction (an act it directs) or definition (a term it fixes) or contract (a promise to its caller) or behavior (what it does) or warrant (why it holds)

A repair runs locate -> diagnose -> change -> verify at each descending grain: a file, a block, a sentence.

Locate the site through whatever named the defect.
Diagnose by naming the flagged unit's job before choosing any change, applying the fix a detector suggests only after that, and reading the enclosing unit for terms you would orphan and conventions you would break.
Change by predicting what the change does, then making the smallest change that keeps the unit's job and clears the defect.
Verify by holding the new text to every standard, the one that flagged its predecessor included.

repair
  | a review note names the defect and the code contradicts the note = surface that to the user and hold every change until they settle it
  | the natural change would alter the unit's job = diagnose again
  | many sites appear to share one diagnosis = confirm on the first two before the rest
  | the change trades the flagged defect for a new one = return to diagnose

<!-- rule: writing-code -->
## writing-code

For all source code you write or modify with its dependencies and every verdict on whether it works, optimize for code that does what its contracts state at the lowest burden of complexity to its future maintainers.

Keep in view the larger work your code joins, and write for a maintainer who reads it years later without having written it.

Write the contracts first: simple interfaces and exchangeable pieces, one interface per module, deep modules.
Keep each contract simple enough that a reader notices its concepts and requirements first.
Write at the altitude and abstraction level the operation sits at.
Keep abstractions composable wherever composing leaves each one's contract unchanged.

### Toolchain

Before the first source file, extend what the repository has into the language's standard toolchain -> write each line to pass it.
Include one version pin every tool reads, a strict type checker, and a commit hook.
Import through the module system, with runtime load-path edits kept out.
Name each module so it imports by name and shadows nothing.
Keep every inline suppression directive out of the code -> restructure until the check passes.

commit hook
  | it skips a formatter, safe autofix, or linter its toolchain offers = add it to run on the staged files with the fixed files restaged

### Design

Give each change one objective.
Build the behavior and mechanism the request names with only the options and cases it names, and leave the rest for a request naming it.
Validate at system boundaries.
Fix the interface before the implementation.
Ask before adding a compatibility layer.
Prefer fewer moving parts, fewer dependencies, fewer assumptions.
Take the smallest working steps: correct first, clear second, fast third.
Add complexity only for a scenario that can happen.
Hold each interface to its contract, and reshape the code behind it to fit.
Ask how someone changes this next, and keep the code simple enough to make that change easy.
Name a thing for what it is.

design
  | an abstraction turns out wrong or fits badly = redesign it, in place of copying code around it
  | shared code branches per caller = split it into abstractions each caller owns
  | an accurate name would join two actions = split the function
  | a function's name alone leaves a caller guessing what the call does = rename it

### Files

Give each file one domain of concern, behind a well-defined boundary and a simple interface.
Keep a same-stem pair, such as `name.js` beside `name.ts`, out of every directory.

file
  | a banner comment would divide it into sections = split it
  | a design puts several concerns in it = split them, in place of following the design's module table
  | you port it to another language = remove the original in the same change as a git rename -> re-point every reference to its old path, ownership files included

Before deleting code that looks unused, search comments too for a caller.
Delete only code with no caller, live or commented.

unused code
  | its only callers are commented out = comment it out beside them
  | the link to a caller is only inferred = ask

### Dependencies

Treat fewer dependencies as no ground for hand-rolling a job, and a missing module as no ground for a standard-library stand-in or for dropping the task.
Install a Python tool with `uv tool install`.
State the package and version in the message that installs it.
Declare every direct dependency at an exact version or a `~` patch range, `~` by default.
Add a package bare, with its version kept off the command line -> narrow the range the package manager wrote.
Leave override floors on transitive packages as the repository's version convention sets them.
Before changing a pinned version, find what binds it, holding a recorded reason as a lead until a run confirms the coupling -> move every package bound to it in the same change.

dependency
  | a common, maintained library does a job the code needs = install it and use it, in place of a hand-rolled implementation
  | an update, add, or audit fix touches a direct one = narrow every `^` it wrote

### Lint rules

Keep every lint rule enabled.
Read a lint rule's own metadata, its fix classification and severity, before predicting what a fix run changes.
Take a git hook's own edits as they land, with diffing or auditing them kept out.

lint rule
  | it conflicts with a compiler strictness flag = change the types or the interface until both pass, the config unchanged
  | its premise misses a package, such as a React hook rule where no React code runs = disable it in that package's own config alone, with a comment linking the rule's docs
  | unsure whether the premise applies = ask before disabling

### Verifying

Verify a change through the plan's checks and the checks the project already has.
Count a finding as fixed or closed only after every part its claim names had a live read.

verify
  | a refactor must keep output = diff every generated artifact byte for byte against a pre-change baseline at each increment
  | a part resists a live read = reach it through another input method, or report exactly what blocks it with the finding left open
  | a check or build fails on a branch with changes = hold the branch as its cause -> find the change that caused it and fix it, with runs on the base and the word "unattributed" kept out
  | a check reports that it ran nothing = count it as a miss, its exit code as no ground for a pass
