---
paths:
  - "**/rules/*.md"
  - "**/CLAUDE.md"
---

WritingRules {
  AppliesWhen { writing or changing a rules file, or CLAUDE.md }

  constraint ValidSudoLang {
    write each rules file as one SudoLang v2 interface, opening on its name
      with no heading and no preamble, and comments nowhere
    write every sentence as an instruction to Claude: an imperative, a
      guarded clause `(condition) => action`, a match arm, a `require`, a
      `warn`, or a field
    (a fact fits no construct) => cut it
    (a path-scoped rule) => keep `paths:` frontmatter whose globs match file
      paths, and still name the activity in Applies
  }

  constraint FiveQualities {
    Trigger  { name in Applies what fires the rule now }
    Demand   { state what it requires, in imperatives }
    Pointer  { (the topic appears in another file) => restate the one clause
               this rule rests on, and keep the full statement in one place }
    Boundary { (a neighbor continues the territory) => name it
               (no neighbor) => let Applies alone bound the rule, and never
                 fabricate a boundary }
    Warrant  { put the mechanism fact the reader cannot see inside the
               instruction that rests on it, and never argue that the rule
               deserves to exist }
  }

  constraint CrossReferences {
    make each file close from itself: point with `via(Name)` only at a
      constraint or fn inside the same interface, and name no node of
      another rules file or agent
    (you rename a node) => sweep its `via()` pointers in the same change
  }

  constraint RoutesByKind {
    route new content before writing it: an invariant to `rules/`, a catalog
      to `references/`, enforcement to a hook, stance to CLAUDE.md
  }
}
