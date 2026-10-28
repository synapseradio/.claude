<!-- rule: writing-code -->

## writing-code

For all source code you write or modify, optimize for code that does what its tests assert, each part distinct and its purpose plain.

Keep in view the larger work your code joins. Write for a maintainer who reads it years later without having written it.

Write the contracts first: simple interfaces, exchangeable pieces, one interface per module, deep modules. Keep each contract simple enough that a reader notices its concepts and requirements first. Choose the tool that fits the job exactly. Write at the altitude and abstraction level the operation sits at. Keep abstractions composable wherever composing leaves each one's contract unchanged.

### Design

Give each change one objective. Build the behavior the request names, with the options, flags, and cases it names, and leave every other behavior for a request naming it. Validate at system boundaries. Fix the interface before the implementation. Ask before adding a compatibility layer. Prefer fewer moving parts, fewer dependencies, fewer assumptions. Take the smallest working steps: correct first, clear second, fast third. Where an abstraction turns out wrong or fits badly, redesign it, in place of copying code around it. Where shared code branches per caller, split it into abstractions each caller owns. Ask how someone changes this next, and keep the code simple enough to make that change easy. Build mechanism only for a scenario the request names. Name a thing for what it is. Where a function's name alone leaves a caller guessing what the call does, rename it. Where an accurate name would join two actions, split the function.

Add complexity only for a scenario that can happen. Hold each interface to its contract, and reshape the code behind it to fit.
