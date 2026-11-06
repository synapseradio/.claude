<!-- rule: comments -->
## comments

For every comment in source code you write or land an edit beside, optimize for a comment written only after the code, a name, a type, a test, and a doc each failed to carry its point.

- referent: the code a comment describes
- page: a documentation page, an issue on a public tracker included
- hold whole: a reader of that carrier alone learns it
- Why: rationale naming each platform or library behavior the referent rests on or is limited by, linking the page that backs it
- Consult: asks whoever changes the area to reach a team the user named first, as in "please reach out to our team before making changes in this area"
- Anchor: the domain fact the code answers to, citing its protocol, spec, or regulation
- Map: a structure in the referent no type carries, a state layout for one, that a reader would otherwise rebuild before changing it
- Hazard: a break in the referent no test can exercise and no page holds
- Summary: one sentence on an exported declaration or at a file's head, saying what it is for

Read every comment skeptically, most of all one claiming an invariant or a guarantee.

Route each piece of knowledge before writing, and keep what an arm sends elsewhere out of comments.

home k
  | about a change or a path the code left, not the code as it stands = the commit, PR, or ticket
  | why an invariant holds = ask the user -> write only on approval
  | a platform or library behavior the code rests on or is limited by, with a page = Why linking it
  | a platform or library behavior with no page = Hazard
  | why a test asserts what it does = Why in the test, linking a page per browser, framework, or library behavior it assumes
  | what an export or a file is for = Summary
  | code, a name, a type, or a test can hold it whole = the first that can, improving code until the comment falls away
  | spans files, or a page holds it whole = docs
  | fits a kind = that kind, one point, attached to its referent
  | otherwise = no comment

Hazard written ? tell the user in conversation, outside every artifact, why no test can exercise it and where you looked for a page.

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
A comment may link a test file covering its referent, with every PR and commit link kept out.

Let each sentence state the one point its referent can't carry, or link that point's source; cut the rest, and any still dense after one rewrite, moving it to a test, doc, or link.
In doubt ? leave it out.
The point needs more words than a caller needs to act ? fix what forced it: rename until the name carries it, split the function until each part explains itself, or move it to a doc -> link it.
A comment outruns its code ? move it to a doc -> link it.
A convention demands a comment per declaration ? write the one sentence a caller needs plus what static analysis and IDE tooling require, JSDoc types under @ts-check for one.
Describe code outside the comment's file only in a test's Why, naming the behavior under test the assertion rests on.
Name of a linked page, test, or file only the behavior relied on.

<!-- rule: data-modeling -->
## data-modeling

For every type, data structure, schema, interface signature, or error channel you design or change, in code or in reasoning about it, optimize for a type that admits only legal states, bought only where it deletes a "should never happen" branch.

- panic: the runtime failure on a state that should never happen

Model with product types, sum types, and exhaustive matching.
A model reaches past them, to GADTs for one ? stop and check whether a value check crept back in.
Count a newtype wrapper as ergonomics, with every state it wraps still admitted.

### The runtime check

Treat every runtime check for a state that should never happen as a modeling decision. Test a state only where the type can represent it.
A runtime check, assertion, or throw guards a state that should never happen ? ask each move's test question below, apply each move whose answer is yes, then model the state out or knowingly accept the panic.
A test must exercise a "should never happen" branch ? strengthen the type until the branch disappears, at the first rung the gain pays for: a precise type > an abstract type with a smart constructor, validated inside, exposing only invariant-preserving methods, its method set closed > a test guarding the invariant, in place of the declined type.

### The moves

Each move carries a step, an example, and a test question.

Model the positive space. List the legal states, one constructor per state. For a user reachable by email, phone, or both, write EmailOnly, PhoneOnly, and Both, where two optional fields also admit a user with both empty. Test: can you list the legal states as cases?

Choose the representation for the code at hand. Pick whichever serves the code reading it, converting at boundaries. For a time range ordered by construction, use a start time plus a duration of zero or more, where two raw timestamps need a check. Test: would another representation let you delete this check?

Let types propagate obligations. Link producers and consumers through the type definition, so a new case makes exhaustive matching report every consumer site. A fourth contact kind added to the union fails every match that lacks it. Test: could a new case leave a consumer the compiler stays silent about?

Buy precision where it deletes a panic. Strengthen the type at the site of a "should never happen" throw, and keep the simplest representation at every other site. An email address stays a plain string until code inspects its structure. Test: does this precision delete a panic?

Move obligations to whoever can discharge them. Use a required parameter over an optional value, and parse loose input into a precise type once at a boundary, then pass it inward. A non-empty list gets parsed at the API edge, where a check returning only a verdict makes every downstream site check again. Test: can the caller handle this failure where this code cannot?

<!-- rule: debugging -->
## debugging

For every problem you debug, optimize for a repair that follows a hypothesis a test decided.

State the active hypothesis before changing anything -> let the cheapest test decide it.
The user identifies a root cause ? investigate that cause first, holding every alternative diagnosis until ruled out.
Your measurement runs against their diagnosis ? voice it once, and investigate their cause either way.
Name the cause only once a test decided it, whoever proposed it.

<!-- rule: repairing -->
## repairing

For every named defect you fix in an artifact, optimize for a repair that clears the defect and keeps the unit's job.

- unit's job: one of evidence, a fact it carries; instruction, an act it directs; definition, a term it fixes; contract, a promise to its caller; behavior, what it does; warrant, why it holds

A repair runs locate, then diagnose, then change, then verify, run again at each descending grain: a file, a block, a sentence.

Locate the site through whatever named the defect: a pattern match, a linter hit, a reader's flag, a failing test, your own read.
A review note names it and the code contradicts the note ? surface that to the user and hold every change until they settle it.

Diagnose by naming the flagged unit's job before choosing any change, applying the fix a detector suggests only after that, and reading the enclosing unit for terms you would orphan and conventions you would break.
The natural change would alter the unit's job ? diagnose again.
Many sites appear to share one diagnosis ? confirm on the first two before the rest.

Change by predicting what the change does, then making the smallest change that keeps the unit's job and clears the defect.

Verify by holding the new text to every standard, the one that flagged its predecessor included.
The change trades the flagged defect for a new one ? return to diagnose.

<!-- rule: writing-code -->
## writing-code

For all source code you write or modify, its tests and dependencies included, and every verdict on whether it works, optimize for code that does what its tests assert, each part distinct and its purpose plain.

Keep in view the larger work your code joins, and write for a maintainer who reads it years later without having written it.

Write the contracts first: simple interfaces, exchangeable pieces, one interface per module, deep modules. Keep each contract simple enough that a reader notices its concepts and requirements first. Choose the tool that fits the job exactly. Write at the altitude and abstraction level the operation sits at. Keep abstractions composable wherever composing leaves each one's contract unchanged.

### Design

Give each change one objective. Build the behavior and mechanism the request names, with the options, flags, cases, and scenarios it names, and leave the rest for a request naming it. Validate at system boundaries. Fix the interface before the implementation. Ask before adding a compatibility layer. Prefer fewer moving parts, fewer dependencies, fewer assumptions. Take the smallest working steps: correct first, clear second, fast third. Add complexity only for a scenario that can happen. Hold each interface to its contract, and reshape the code behind it to fit.
An abstraction turns out wrong or fits badly ? redesign it, in place of copying code around it.
Shared code branches per caller ? split it into abstractions each caller owns.
Ask how someone changes this next, and keep the code simple enough to make that change easy. Name a thing for what it is.
A function's name alone leaves a caller guessing what the call does ? rename it.
An accurate name would join two actions ? split the function.

### Files

Give each file one domain of concern, behind a well-defined boundary and a simple interface.
A banner comment would divide one file into sections ? split the file.
A design puts several concerns in one file ? split them, in place of following the design's module table.
Port a file to another language ? remove the original in the same change, as a git rename -> re-point every reference to its old path, ownership files included. Keep a same-stem pair, `name.js` beside `name.ts` for one, out of every directory.

Before deleting code that looks unused, search comments too for a caller.
Its only callers are commented out ? comment it out beside them.
The link to a caller is only inferred ? ask.
Delete only code with no caller, live or commented.

### Dependencies

A common, maintained library does a job the code needs ? install it and use it, in place of a hand-rolled implementation. Treat fewer dependencies as no ground for hand-rolling that job, and a missing module as no ground for a standard-library stand-in or for dropping the task. Install a Python tool with `uv tool install`. State the package and version in the message that installs it.

Declare every direct dependency at an exact version or a `~` patch range, `~` by default. Add a package bare, with its version kept off the command line -> narrow the range the package manager wrote. An update, add, or audit fix touches a direct dependency ? narrow every `^` it wrote. Leave override floors on transitive packages as the repository's version convention sets them.
Before changing a pinned version, find what binds it, holding a recorded reason as a lead until a run confirms the coupling -> move every package bound to it in the same change.

### Lint rules

Keep every lint rule enabled.
A lint rule and a compiler strictness flag conflict ? change the types or the interface until both pass, the config unchanged.
A lint rule's premise misses a package, a React hook rule where no React code runs for one ? disable it in that package's own config alone, with a comment linking the rule's docs.
Unsure whether the premise applies ? ask before disabling.
Read a lint rule's own metadata, its fix classification and severity, before predicting what a fix run changes.
Take a git hook's own edits as they land, with diffing or auditing them kept out.

### Testing

Verify through the plan's checks and a test written red-first for each new behavior, watched failing for the right reason. Judge an existing test by reading it. Keep mutation checks out of the work and every prompt: deliberately broken code, scratch mutants, and temporary failing assertions.

Treat a test count, total or passing, as no evidence a change is safe and as no acceptance criterion. Name the property a change promises -> check that property directly.
A refactor must keep output ? diff every generated artifact byte for byte against a pre-change baseline at each increment.

A test would assert behavior suspected wrong and still undecided ? write it as a todo test, `it.todo()` for one, its intended assertion commented out beneath a block comment stating the mechanism, the stake for whoever uses the product, and the options unranked. Keep schedule, ticket, and owner out of that comment. Keep every green assertion on a suspected defect out of a suite, one beside a hazard comment included.

Count a finding as fixed or closed only after every part its claim names, each direction, host, and variant, had a live read.
A part resists testing ? reach it through another input method, or report exactly what blocks it, the finding left open.

A test or build fails on a branch with changes ? hold the branch as its cause -> find the change that caused it and fix it, with runs on the base and the word "unattributed" kept out.
A run reports no tests found ? count it as a miss, its exit code as no ground for a pass -> run the suite through the runner its own package declares.

Mock GraphQL at the network boundary, MSW for one, in place of module mocks of the query hook or the store it feeds.
Test each repository's behavior in its own suite alone, with a sibling repository's paths, CLI, and installed copies kept out of every test. Keep each of two isolated repositories' paths and tools out of the other's code and commits.
A test sources code that would load a sibling repository ? point that loader at a missing path, so the result holds whether the sibling is installed or not.
