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
