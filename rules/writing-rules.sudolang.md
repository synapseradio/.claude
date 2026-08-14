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
  via(WritingProse)     // sentence-level style
  via(WritingComments)  // comment discipline

  FiveQualities {
    // a rule reads clearly at one point when the reader can answer five
    // questions without leaving it. each can fail while the others hold
    Trigger  { does this fire now?
               (always-on)   => an Applies block, first line inside the rule
               (path-scoped) => `paths:` frontmatter, with Applies still
                 naming the activity
                 // the machine reads the globs, the reader the Applies }
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
                   // the absence is the fact worth stating, and it marks
                   // a file worth writing if that ground ever needs rules
               }
             }
    Warrant  { why does it hold? a comment carrying the mechanism fact
               the reader cannot see from where they stand
               // warrant states a fact. justification argues that the
               // rule deserves to exist, and never gets written }
  }

  CrossReferences {
    the full statement lives in one place, and every other mention carries
      its local consequence and points there
    core rules cite only core rules: an expansion in any other file points
      at its numbered line, and the line never points back out
    a pointer carries a comment beside it naming what lives at the far
      end, and addresses its target by match (the target) {
      case (always-on, and its object name kebab-cases to its filename) =>
        the object name: via(CoreRules.8.GroundOrMark), via(Claims.Opinions)
        // the corpus inlines into one context each session, where the
        // object sits nearer the reader than any path
      case (path-scoped, under references/, or named unlike its object) =>
        the path: via(./decompose-everything.sudolang.md Asking)
        // the reader may hold no copy in context, so the address must
        // resolve on disk
    }
    edits land where the full statement lives, and the pointers follow
    when a summary cites an expansion, the expansion points back
      // a reader landing at either end learns the pair stays in sync
    citations bind to headings and node names, so renaming one sweeps its
      citations in the same change
      // core-rules numbers carry a stronger promise: stable across
      // restructurings
  }

  LoadClasses {
    always-on   { no frontmatter, loads every session }
    path-scoped { `paths:` frontmatter, loads when a matching file
                  enters play }
    when an always-on rule commands work in path-scoped territory, it names
      the file that will arrive
      // the reader otherwise cannot suspect what they have not loaded
  }

  RoutesByKind {
    new content routes before it gets written: an invariant to rules/,
      a catalog to references/, enforcement to a hook, stance to CLAUDE.md
      // the routing itself lives in CLAUDE.md, "What lives where"
  }
}
