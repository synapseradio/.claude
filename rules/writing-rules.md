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
    open the interface on `AppliesWhen { }` naming what fires the rule, and
      give a constraint its own `AppliesWhen { }` only where it fires on
      less than the interface does
    write every sentence as an instruction to Claude: an imperative, a
      guarded clause `(condition) => action`, a `warn (condition) => action`,
      a `require`, a `let`, a `for each` or `while`, a pipeline of `|>`
      steps, a `match`, a `test { }` question inside a catalog member, or a
      field
    (a fact fits no construct) => cut it
    (a path-scoped rule) => keep `paths:` frontmatter whose globs match file
      paths, and still name the activity in AppliesWhen
  }

  constraint Containers {
    put every demand inside `constraint Name {` or `fn name() {`, and keep a
      bare `Name {` block for definitions alone: a record, a catalog of
      kinds, a value table
    write a kind the text matches against as `Name { text }`, a value a
      statement compares against as `name { text }`, a field as `name: type`
      or `name = value`, and a list as `name = [items]`
    give every node a name unique in its file, with no number in front,
      and every interface a name unique across rules/ and agents/
    write a match as `match (subject) {` with `case (condition) => action`
      arms and an optional `default => action`, and let the first matching
      arm win without saying so
  }

  constraint Forms {
    write a prohibition as `require you never <act>` where the model acts,
      and `require no <thing> <happens>` where the ban falls on an artifact
      or a state
    keep `, never X` and `, and never X` for a contrast inside an
      imperative
    write a condition that gates a whole statement as a guard, and keep a
      trailing `unless`, `only where`, `wherever`, or `where` clause for one
      that qualifies the action
    end a statement that applies another node with `via(Name)` on its last
      line, and write `via(Name)` alone on the line closing a fn body where
      the whole fn runs under it
    inside a catalog, write a member that holds a definition as `Name {
      text }` and a member that instructs as an imperative or guard
  }

  constraint FiveQualities {
    Trigger  { name in AppliesWhen what fires the rule now }
    Demand   { state what it requires, in imperatives }
    Pointer  { (the topic appears in another file) => restate the one clause
               this rule rests on, and keep the full statement in one place }
    Boundary { (a neighbor continues the territory) => name it
               (no neighbor) => let AppliesWhen alone bound the rule, and never
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
