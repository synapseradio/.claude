<!-- rule: writing-code -->

## writing-code

For all source code you write or modify, optimize for code that does what its tests assert, each part distinct and its purpose plain.

Keep in view the larger work your code joins. Write for the maintainer who reads it years from now without having written it.

Write the contracts first. Keep each contract simple enough that its concepts and requirements are the first thing a reader notices. Choose the tool that fits the job. Write at the level of abstraction the operation sits at.

### Design

Validate at system boundaries. Fix the interface before writing the implementation. Before a compatibility layer, ask first. Prefer fewer moving parts, fewer dependencies, fewer assumptions. Take the smallest working steps: correct first, clear second, fast third. Where an abstraction turns out wrong, redesign it. Where shared code branches per caller, split it into abstractions each caller owns. Ask how someone changes this next, then make that change easy. Name a thing for what it is. Where a function needs a comment to say what it does, rename it.

Never add complexity for a scenario that cannot happen. Never copy code to get around an abstraction that fits badly. Never reshape an interface to fit the code written behind it.
