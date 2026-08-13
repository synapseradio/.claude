---
paths:
  - "**/rules/*.md"
  - "**/CLAUDE.md"
---

# Writing Rules

```sudolang
WritingRules {
  Applies { writing or changing a rules file, or CLAUDE.md }
  // this file speaks to what makes a rule legible at the point where
  // a reader meets it
  via(./writing-prose.md)     // sentence-level style
  via(./writing-comments.md)  // comment discipline

  FiveQualities {
    // a rule reads clearly at one point when the reader can answer five
    // questions without leaving it. each can fail while the others hold
    Trigger  { does this fire now?
               always-on   -> an Applies block, first line inside the rule
               path-scoped -> `paths:` frontmatter, with Applies still
                 naming the activity
                 // the machine reads the globs, the reader the Applies }
    Demand   { what does it require? the body says so, in imperatives }
    Pointer  { the topic appears in other files too -> name where the
               full statement lives }
    Boundary { where does this rule stop?
               a neighbor continues the territory -> name it
               no neighbor, and none missed      -> Applies alone bounds
                 the rule; never fabricate a seam
               no neighbor, and a reader would assume coverage past the
                 edge -> say the territory sits ungoverned
                 // the absence is the fact worth stating, and it marks
                 // a file worth writing if that ground ever needs rules }
    Warrant  { why does it hold? a comment carrying the mechanism fact
               the reader cannot see from where they stand
               // warrant states a fact. justification argues that the
               // rule deserves to exist, and never gets written }
  }

  CrossReferences {
    the full statement lives in one file; every other mention carries
      its local consequence and points there
    a pointer writes as via(<file [Node]>), with a comment beside it
      naming what lives at the far end
    edits land where the full statement lives, and the pointers follow
    a summary cites an expansion -> the expansion points back
      // a reader landing in either file learns the pair stays in sync
    citations bind to headings and node names
      -> renaming one sweeps its citations in the same change
      // core-rules numbers carry a stronger promise: stable across
      // restructurings
  }

  LoadClasses {
    always-on   { no frontmatter; loads every session }
    path-scoped { `paths:` frontmatter; loads when a matching file
                  enters play }
    an always-on rule commands work in path-scoped territory
      -> it names the file that will arrive
      // the reader otherwise cannot suspect what they have not loaded
  }

  RoutesByKind {
    new content routes before it gets written: an invariant to rules/,
      a catalog to references/, enforcement to a hook, stance to CLAUDE.md
      // the routing itself lives in CLAUDE.md, "What lives where"
  }
}
```
