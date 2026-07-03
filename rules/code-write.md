# Writing or Modifying Code

When writing or modifying source code.

Never add complexity for scenarios that cannot happen.

Validate at system boundaries. Ask before adding compatibility layers.

Prefer simplicity over cleverness. Fewer moving parts, fewer dependencies, fewer assumptions.

Work incrementally. Take the smallest working steps. Aim for clear first, correct second, fast third — never all at once. Separate refactoring from behavior changes.

Prefer duplication over wrong abstraction. Do not deduplicate unless the pieces represent the same concept and change for the same reasons. Inline shared code that branches per caller.

Design for change. Ask "how will someone change this next?" Make the next change easy.

Names describe the thing itself, not how it is made. Comments explain why, never what. If a function needs a comment to explain what it does, rename it.

Make invalid states impossible. Use types to enforce constraints.

Deep modules, simple interfaces. The interface should not grow with the implementation.
