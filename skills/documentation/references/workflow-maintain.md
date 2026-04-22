# Workflow: Maintain Documentation

<!--
execution: inline
parallelism: sequential
needs-user-interaction: false
-->

## Role

Documentation maintainer. Fight rot on an existing doc set: link decay, external-claim drift, missing owners, stale content.

## Task

Produce a maintenance-action plan for the doc set named by the user. The plan assigns an owner per doc, runs the link-check, re-verifies external claims, and triages review effort via GitLab's levels of edit.

## Onboarding

Before starting, load:

1. `references/rot-prevention.md` — docs-as-code, Scribelet's three mitigations, GitLab levels of edit.
2. `references/sourcing-and-citations.md` — external-claim drift rule.
3. `references/review-rubric.md` — section 5 (staleness) in particular.

## Process

Use `TaskCreate` to track each step. Six steps.

1. **Enumerate the docs in scope.** Build a list of doc paths. If three or more, create one task per doc.
2. **Assign or confirm an owner per doc.** For each doc, identify the owner. If none exists, assigning one is the highest-leverage intervention (see `rot-prevention.md`, Scribelet's three mitigations). Record the owner in the plan.
3. **Run the link checker.** Execute `scripts/check-doc-links.sh <path>`. Capture output. Every broken link is a finding.
4. **Re-verify external claims.** For each external claim in each doc, re-fetch the cited URL (WebFetch or Tavily) and compare the quoted or paraphrased content against the current source. Record each drifted claim as a finding.
5. **Triage by GitLab's levels of edit.** Classify each doc as *light*, *medium*, or *heavy* edit. Mission-critical docs and public-facing reference get heavy; ephemeral internal notes get light. Source: https://handbook.gitlab.com/handbook/product/ux/technical-writing/
6. **Produce the maintenance-action plan.** Group by doc; list owner, edit level, broken links, drifted claims, and next action.

## Plan template

```
# Maintenance Plan for <doc set>

## Per-doc entries

### <path/to/doc-1.md>
- Owner: <name or "unassigned — assign before release">
- Edit level: <light | medium | heavy>
- Broken links (from check-doc-links): <N; list below>
- Drifted claims (from re-verification): <N; list with original and current text>
- Last verified: <YYYY-MM-DD> (practitioner pattern, not doctrine — apply if project already stamps)
- Next action: <specific fix, with estimated effort>

## Summary
- Total docs: N
- Unowned: M
- Broken links: K
- Drifted claims: J
- Recommended cadence by level:
  - heavy: quarterly re-verification
  - medium: biannual
  - light: yearly or on-change only
```

## Success Conditions

- Every doc in scope has a named owner or is flagged as *unassigned* with a recommended assignee.
- `check-doc-links.sh` ran against every doc path; output is captured.
- Every external claim was re-fetched from its primary source and compared; drift is recorded.
- Each doc has a GitLab-style edit level assigned with a one-sentence reason.

## Why

Scribelet's research names three mitigations for rot: link checkers, external-claim verification, and named owners. This workflow exercises all three. GitLab's levels-of-edit pattern prevents applying the same review cadence to every doc — mission-critical docs warrant heavy review, ephemeral ones do not. See https://scribelet.app/blog/outdated-documentation and https://handbook.gitlab.com/handbook/product/ux/technical-writing/ for the grounding.
