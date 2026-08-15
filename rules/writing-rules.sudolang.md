---
paths:
  - "**/rules/*.md"
  - "**/CLAUDE.md"
---

# Writing Rules

What makes a rule legible at the point where a reader meets it: five questions
the reader can answer without leaving the rule, the pointer discipline that
keeps one full statement in one place, and how a file gets loaded at all.

WritingRules {
  Applies { writing or changing a rules file, or CLAUDE.md }
  write every sentence under via(WritingProse)

  Carriers {
    write every fact into an imperative, a guarded clause, a match arm, or a
      Constraints entry, and never into a comment
    (a fact fits no construct) => cut it
    (a comment carries an obligation nothing else states) => write it as a
      live imperative
    a comment in source code answers to via(WritingComments), and a rules
      file carries none
  }

  FiveQualities {
    Trigger  { does this fire now?
               (always-on)   => an Applies block, first line inside the rule
               (path-scoped) => `paths:` frontmatter, whose globs match file
                 paths alone, with Applies still naming the activity }
    Demand   { what does it require? the body says so, in imperatives }
    Pointer  { when the topic appears in other files too, name where the
               full statement lives }
    Boundary { where does this rule stop?
               match (the edge) {
                 case (a neighbor continues the territory) =>
                   name it
                 case (no neighbor, and none missed) =>
                   Applies alone bounds the rule. never fabricate a seam
                 case (no neighbor, and a reader would assume coverage
                       past the edge) =>
                   say the territory sits ungoverned
               }
             }
    Warrant  { why does it hold? put the mechanism fact the reader cannot
               see from where they stand inside the instruction that rests
               on it, and never argue that the rule deserves to exist }
  }

  CrossReferences {
    Constraints {
      the full statement lives in one place, and every other mention carries
        its local consequence and points there
      core rules cite only core rules: an expansion in any other file points
        at its numbered line, and the line never points back out
      edits land where the full statement lives, and the pointers follow
      when a summary cites an expansion, the expansion points back
      cite a numbered core rule by its number, and cite everything else by
        heading or node name, an unnumbered core rules block included
      (you rename a heading or a node) => sweep its citations in the same
        change
    }

    fn address(target) {
      address it by
      match (the target) {
        case (always-on, and its object name kebab-cases to its filename) =>
          the object name: via(CoreRules.8.GroundOrMark), via(Claims.Opinions)
        case (path-scoped, under references/, or named unlike its object) =>
          the path, written to resolve on disk:
            via(./decompose-everything.sudolang.md Asking)
      }
    }
  }

  LoadClasses {
    always-on   { no frontmatter, loads every session }
    path-scoped { `paths:` frontmatter, loads when a matching file
                  enters play }
    when an always-on rule commands work in path-scoped territory, it names
      the file that will arrive
  }

  RoutesByKind {
    route new content before you write it, following CLAUDE.md under "What
      lives where": an invariant to rules/, a catalog to references/,
      enforcement to a hook, stance to CLAUDE.md
  }
}
