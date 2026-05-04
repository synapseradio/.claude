# Writing or Modifying Code

<when> writing or modifying source code.

<never> Add complexity for scenarios that cannot happen.
<prefer> Validate at system boundaries. Ask before adding compatibility layers.

<prefer> Simplicity over cleverness. Fewer moving parts, fewer dependencies, fewer assumptions. A plain loop over a chain of higher-order functions.
<prefer> Work incrementally. Smallest working steps. Order: clear, correct, then fast — never at the same time. Separate refactoring from behavior changes.
<prefer> Duplication over wrong abstraction. Do not deduplicate unless the pieces represent the same concept and change for the same reasons. Inline shared code that branches per caller.
<prefer> Design for change. Ask "how will someone change this next?" Make the next change easy.
<prefer> Names describe what something is, not how it is made. Comments explain why, never what. If a function needs a comment to explain what it does, rename it.
<prefer> Make invalid states impossible. Enums over boolean flags. Required fields over optional defaults. Types enforce constraints.
<prefer> Deep modules, simple interfaces. A 3-parameter function doing significant work beats a 10-parameter function doing little.
