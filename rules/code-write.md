---
paths:
  - "**/*.ts"
  - "**/*.tsx"
  - "**/*.js"
  - "**/*.jsx"
  - "**/*.mjs"
  - "**/*.cjs"
  - "**/*.py"
  - "**/*.go"
  - "**/*.rs"
  - "**/*.rb"
  - "**/*.java"
  - "**/*.kt"
  - "**/*.swift"
  - "**/*.c"
  - "**/*.cc"
  - "**/*.cpp"
  - "**/*.cxx"
  - "**/*.h"
  - "**/*.hpp"
  - "**/*.cs"
  - "**/*.php"
  - "**/*.scala"
  - "**/*.clj"
  - "**/*.ex"
  - "**/*.exs"
  - "**/*.erl"
  - "**/*.lua"
  - "**/*.zig"
  - "**/*.nim"
  - "**/*.dart"
  - "**/*.elm"
  - "**/*.hs"
  - "**/*.ml"
  - "**/*.fs"
  - "**/*.r"
---

# Writing or Modifying Code

## Boundaries on complexity

- Never add complexity for scenarios that cannot happen. Validate at system boundaries only. Ask before adding compatibility layers.

## How to Write Code

- **Simplicity over cleverness.** Choose fewer moving parts, fewer dependencies, fewer assumptions. Prefer a plain readable loop over a clever chain of higher-order functions.
- **Work incrementally.** Break changes into the smallest working steps. Order: make it clear, make it work, make it right, make it fast — never at the same time. Keep refactoring separate from behavior changes.
- **Duplication over wrong abstraction.** Do not deduplicate unless the pieces represent the same concept and change for the same reasons. If shared code branches per caller, inline it.
- **Optimize for change.** Ask "how will someone change this next?" Make the next change easy. Readable and changeable beats elegant and rigid.
- **Clarity is mandatory.** Names describe what something represents, not how it's implemented. Comments explain why, never what. If a function needs a comment to explain what it does, rename it.
- **Make invalid states impossible.** Prefer enums over boolean flags. Prefer required fields over optional-with-defaults. Use types to enforce constraints.
- **Deep modules, simple interfaces.** Hide internal complexity behind simple interfaces. A 3-parameter function doing significant work beats a 10-parameter function doing little.
