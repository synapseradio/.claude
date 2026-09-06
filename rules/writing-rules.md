---
paths:
  - "**/rules/*.md"
  - "**/CLAUDE.md"
---

# Writing rules

This applies when writing or changing a rules file, or CLAUDE.md.

A rules file exists so the model decides the same way every turn and still knows what the decision serves where the machine runs out. A block line with a warrant inside it makes the reader parse the why to find the what, so every warrant lives in the values paragraph and each block line goes bare. A rule that argues for itself spends the reader's attention on a decision the user already took.

## Form

Write each rules file as markdown: one heading naming the territory, then a sentence naming what fires the rule, in the form "This applies when ...", then a values paragraph of one to four sentences stating what the rule values in the output and what a wrong output costs, carrying every warrant the file has, then one sudolang block carrying the machine. Give a subsection its own applies-when sentence only where it fires on less than the file does. For a path-scoped rule, keep `paths:` frontmatter whose globs match file paths, and still name the activity in the applies-when sentence.

The pre-commit hook renders CLAUDE.md and the always-on rules into `~/.claude/references/working-rules.md` through `scripts/sync-agent-configs.py`, in the order its `WORKING_RULES_ORDER` tuple names, so never edit the render, and add a new always-on rule's file stem to that tuple in the same change.

## The machine

```sudolang
Rule {
  values: prose before the block, every warrant, no argument for the rule's existence
  machine: one block
  a thing moved through states => a State block naming them
  a decision => match arms
  a procedure => fn or a pipeline
}

Machine {
  State { kind: A | B }
  transition = input => match (input) {
    case pattern => act, next state
    default => act
  }
  Constraints { an invariant that is neither a value nor a transition }
  require a halt, one per line
}

Validity {
  every arm inside a match opens with case, the fallback with default
  an arm outside a match opens with its condition and no case
  a function reads fn name(args) { } or name = args => expr
  a union reads A | B
  a state set reads State { kind: A | B }
  a block holds no otherwise, no dotted definition, no bracket property name,
    no dollar sign outside a string, no comment, no parenthetical gloss
}

Qualities {
  trigger: the applies-when sentence names what fires the rule now
  demand: the machine states what the rule requires
  pointer: the topic appears in another file => restate the one clause this rule
    rests on, keep the full statement in one place, write no link between rules files
  boundary: a neighbor continues the territory => name it; none does =>
    the applies-when sentence alone bounds the rule
  warrant: the values prose carries it; a block line carries none
}
```

## Routing

Route new content before writing it: an invariant to `rules/`, a catalog to `references/`, enforcement to a hook, stance to CLAUDE.md. When you rename a rules file or a heading another file links, sweep the links in the same change.
