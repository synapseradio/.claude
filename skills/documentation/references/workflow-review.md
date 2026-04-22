# Workflow: Review Documentation

<!--
execution: inline
parallelism: sequential
needs-user-interaction: false
-->

## Role

Documentation reviewer. Apply the rubric to an existing doc, produce a structured report, cite every finding.

## Task

Audit one or more existing docs against the rubric in `references/review-rubric.md`. Produce a report grouping findings by rubric section. Cite the source URL for every rule invoked.

## Onboarding

Before reviewing, load:

1. `references/review-rubric.md` — the checklist.
2. `references/diataxis-taxonomy.md` — for classification claims.
3. `references/voice-and-style.md` — for voice and forbidden-word findings.
4. `references/sourcing-and-citations.md` — for citation-gap findings.

## Process

Use `TaskCreate` to track each step as a task. Seven steps.

1. **Enumerate the docs to review.** Create a list; one task per doc if three or more.
2. **Classify each doc.** Apply the Diátaxis compass. Record the classification as the first line of each doc's findings.
3. **Run the rubric top-to-bottom on each doc.** Do not skip sections. For each item, mark pass, fail, or n/a.
4. **Run the scripts.** `scripts/find-forbidden-words.sh` on each doc; `scripts/check-doc-links.sh` for link staleness. Capture output.
5. **Triage script hits.** Not every forbidden-word hit is a failure. Read the context; mark each as *true fail*, *acceptable in context*, or *ambiguous*.
6. **Check external-claim freshness.** For each external claim in the doc, re-fetch the cited source (via WebFetch or Tavily) and compare. Note drift as a finding under section 5 of the rubric.
7. **Produce the report.** Group findings by rubric section number. Each finding cites the source URL of the rule it invokes, not this skill.

## Report template

```
# Review of <doc path>

## Classification
- Quadrant: <tutorial | how-to | reference | explanation>
- Compass answer: <action | cognition> + <acquisition | application>

## Findings

### 1. Classification
- [fail] The doc conflates tutorial and how-to: <evidence>. Source: https://diataxis.fr/map/

### 2. Per-quadrant discipline
...

### 3. Voice and style
...

### 4. Sourcing and honesty
...

### 5. Staleness
- [fail] External claim "X" has drifted. Source at <URL> now says "Y". Source for rule: https://scribelet.app/blog/outdated-documentation

### 6. Information design
...

### 7. Shipping essentials (project-level only)
...

## Summary
- N failures, M acceptable-in-context, K ambiguous, J pass.
- Top three fixes, ordered by rubric section.
```

## Success Conditions

- Every finding in the report cites a source URL.
- The rubric was run in full; no section was skipped.
- Every forbidden-word hit was triaged (true fail, acceptable in context, or ambiguous) — not blindly flagged.
- External-claim freshness was checked against primary sources.

## Why

A review report is only useful if the reader can act on it. Citing the source for each rule lets the doc's owner adjudicate the finding themselves. Triaging the forbidden-words list prevents busywork; Google's and Django's intent is diminishing uses, not every grammatical instance (see `voice-and-style.md` for the quoted sources).
