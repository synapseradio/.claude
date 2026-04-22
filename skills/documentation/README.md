# documentation

Agent Skill for writing, reviewing, and maintaining technical and conceptual documentation. Grounded in the Diátaxis four-quadrant taxonomy (Procida, https://diataxis.fr/), the convergent style guidance of Google / Microsoft / GitLab / Django, Raymond's Unix documentation honesty rule, Knuth's docs-as-literature stance, Tufte's data-ink principle, and docs-as-code rot prevention. Every rule in the skill traces to a primary source URL — no fabricated authorities.

## Install

This skill lives at `~/.claude/skills/documentation/` (personal, across all projects). No install command is needed if the skill is authored in place. To copy elsewhere:

```sh
cp -r ~/.claude/skills/documentation /path/to/target/skills/
```

## What it does

- **Classifies** any doc against the Diátaxis compass: tutorial, how-to, reference, or explanation.
- **Writes** new docs by type-specific rules, with every external claim cited.
- **Reviews** existing docs against a checklist rubric with source citations per rule.
- **Maintains** doc sets against rot via link checking, external-claim re-verification, owner assignment, and GitLab-style levels of edit.

## References

| File | Purpose |
|------|---------|
| `references/diataxis-taxonomy.md` | Four quadrants, the compass, the map; how to classify a doc |
| `references/writing-by-type.md` | Per-quadrant rules: include, exclude, analogies |
| `references/explanation-craft.md` | Mental-model docs: connections, design history, answering *why* |
| `references/voice-and-style.md` | Active voice, forbidden words, tone per Google/Microsoft/GitLab/Django |
| `references/sourcing-and-citations.md` | Every external claim cites a URL; Raymond's honesty rule |
| `references/rot-prevention.md` | Docs-as-code, owners, always-complete-never-finished |
| `references/info-design-diagrams.md` | Tufte data-ink, chartjunk, screenshot caution |
| `references/review-rubric.md` | Checklist for auditing existing docs |
| `references/workflow-author.md` | Step-by-step authoring workflow |
| `references/workflow-review.md` | Step-by-step review workflow |
| `references/workflow-maintain.md` | Freshness and rot-prevention workflow |

## Scripts

| Script | Purpose |
|--------|---------|
| `scripts/check-doc-links.sh` | Wraps `lychee` for link checking; graceful fallback if not installed |
| `scripts/find-forbidden-words.sh` | Scans markdown for diminishing words per Google and Django |

## Examples

The `examples/` directory holds one short exemplar per Diátaxis quadrant. Read them when a reference alone leaves the shape unclear.

| File | Quadrant |
|------|----------|
| `examples/tutorial.md` | Tutorial |
| `examples/how-to.md` | How-to guide |
| `examples/reference.md` | Reference |
| `examples/explanation.md` | Explanation |

## Usage

**Writing a tutorial:**

> "Write a tutorial for first-time users of our CLI."

The skill loads `diataxis-taxonomy.md`, `writing-by-type.md`, `voice-and-style.md`, `workflow-author.md`, classifies the doc as a tutorial, and drafts it with the tutorial quadrant's rules applied.

**Reviewing a doc set:**

> "Review the docs in `docs/` for staleness and category drift."

The skill loads `review-rubric.md`, `workflow-review.md`, and `workflow-maintain.md`, runs the rubric, runs the scripts, and produces a report citing the rule's source URL for each finding.

## License

MIT
