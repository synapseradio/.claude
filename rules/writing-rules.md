---
paths:
  - "**/rules/*.md"
  - "**/CLAUDE.md"
---

# Writing rules

This applies when writing or changing a rules file, or CLAUDE.md.

## Form

Write each rules file as markdown: one heading naming the territory, then a sentence naming what fires the rule, in the form "This applies when ...". Give a subsection its own applies-when sentence only where it fires on less than the file does. Carry procedure and decision structure in ```sudolang blocks and everything else in prose, keeping each warrant inside the line that rests on it. Write comments nowhere.

Write every sentence and block line as an instruction to Claude: an imperative, a condition and the act it gates, or a definition an instruction uses. Cut a sentence that only describes, argues, or narrates.

For a path-scoped rule, keep `paths:` frontmatter whose globs match file paths, and still name the activity in the applies-when sentence.

`~/.claude/references/working-rules.md` renders the always-on rules into one document. A change to an always-on rule lands in the rule's file and in that document in the same change.

## Five qualities

```sudolang
Qualities {
  trigger: the applies-when sentence names what fires the rule now
  demand: state what the rule requires, in imperatives
  pointer: the topic appears in another file => restate the one clause this rule
    rests on, keep the full statement in one place, link the file that carries it
  boundary: a neighbor continues the territory => name it; none does =>
    the applies-when sentence alone bounds the rule, fabricating no boundary
  warrant: put the mechanism fact the reader cannot see inside the instruction
    that rests on it, and never argue that the rule deserves to exist
}
```

## Routing

Route new content before writing it: an invariant to `rules/`, a catalog to `references/`, enforcement to a hook, stance to CLAUDE.md. When you rename a rules file or a heading another file links, sweep the links in the same change.
