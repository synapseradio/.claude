<!-- rule: comments -->
## comments

For every comment in source code you write or land an edit beside, a docstring, JSDoc, or TODO included, optimize for a comment written under the mandatory `comments` skill: before writing a comment, editing one, or landing an edit to code that has a comment beside it, load `comments` through the Skill tool once in this context, or read `~/.claude/skills/comments/SKILL.md` in full where the Skill tool is absent, and follow it in every comment you write and every edit you land beside one.

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

<!-- rule: toolchain -->
## toolchain

For every repository's toolchain and lint rules and every dependency you add or change, optimize for code that passes the checks the toolchain runs, on dependencies pinned the way the repository pins them.

### Toolchain

Before the first source file, extend what the repository has into the language's standard toolchain -> write each line to pass it.
Include one version pin every tool reads, a strict type checker, and a commit hook.
Import through the module system, with runtime load-path edits kept out.
Name each module so it imports by name and shadows nothing.
Keep every inline suppression directive out of the code -> restructure until the check passes.

commit hook
  | it skips a formatter, safe autofix, or linter its toolchain offers = add it to run on the staged files with the fixed files restaged

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

<!-- rule: writing-code -->
## writing-code

For all source code you write or modify with its dependencies and every verdict on whether it works, optimize for code that does what its contracts state at the lowest burden of complexity to its future maintainers.

Keep in view the larger work your code joins, and write for a maintainer who reads it years later without having written it.

Write the contracts first: simple interfaces and exchangeable pieces, one interface per module, deep modules.
Keep each contract simple enough that a reader notices its concepts and requirements first.
Write at the altitude and abstraction level the operation sits at.
Keep abstractions composable wherever composing leaves each one's contract unchanged.

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

### Verifying

Verify a change through the plan's checks and the checks the project already has.
Count a finding as fixed or closed only after every part its claim names had a live read.

verify
  | a refactor must keep output = diff every generated artifact byte for byte against a pre-change baseline at each increment
  | a part resists a live read = reach it through another input method, or report exactly what blocks it with the finding left open
  | a check or build fails on a branch with changes = hold the branch as its cause -> find the change that caused it and fix it, with runs on the base and the word "unattributed" kept out
  | a check reports that it ran nothing = count it as a miss, its exit code as no ground for a pass
