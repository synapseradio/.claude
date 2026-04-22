# Rot Prevention

Docs go stale. The convergent practitioner answer: treat docs like code, assign owners, verify external claims, and publish organically instead of in a plan-then-publish burst.

## Primary sources

| URL | Topic |
|-----|-------|
| https://www.writethedocs.org/guide/docs-as-code/ | Write the Docs — Docs as Code |
| https://docslikecode.com/about/ | Docs Like Code (Anne Gentle) |
| https://scribelet.app/blog/outdated-documentation | Scribelet — external-claim drift |
| https://www.knowledgeowl.com/blog/posts/always-complete-never-finished | Procida's "always complete, never finished" (recap of Write the Docs talk) |
| https://handbook.gitlab.com/handbook/product/ux/technical-writing/ | GitLab — levels of edit and stage-group ownership |
| https://www.writethedocs.org/guide/writing/beginners-guide-to-docs/ | Write the Docs — the essentials every project should ship |

## Docs as code

Write the Docs names the movement:

> The guide is a hub for "concepts [that] are widely practiced in the software industry, and are gaining adoption in the writing community."
>
> — https://www.writethedocs.org/guide/docs-as-code/

Docs Like Code states the pattern plainly: same repo as the code, same review, same CI/CD.

> Docs Like Code (Anne Gentle): treat docs like code — same repo, same CI/CD, same review. See Read the Docs, GitHub Pages, Netlify integrations.
>
> — https://docslikecode.com/about/

The operational moves fall out: docs live next to code, PRs touch both, CI runs on docs (link-check, lint, build).

## Scribelet's three mitigations

> "Docs-as-code makes documentation maintainable in principle... Reference docs go stale when external systems they describe ship breaking changes (a dependency, an API, a vendor configuration). A combination [works]: link checkers for dead URLs, AI verification for external-claim drift, and a named owner per doc for everything tooling can't catch."
>
> — https://scribelet.app/blog/outdated-documentation

Three moving parts:

1. **Link checker** — catches dead URLs. `scripts/check-doc-links.sh` wraps `lychee`.
2. **External-claim verification** — catches drift in vendor behaviour, API signatures, version numbers. Tooling alone does not cover this; a human or an AI with access to the source must re-check.
3. **Named owner per doc** — catches everything tooling cannot.

No single mechanism suffices. Use the three together.

## Always complete, never finished

Procida's framing of documentation as organic growth:

> "A plant grows through an organic process when it grows... it's an organism that's always complete, and always ready to progress to the next step of growth. It's never finished because there's always another step in its development."
>
> — https://www.knowledgeowl.com/blog/posts/always-complete-never-finished (paraphrased summary of Procida's Write the Docs talk)

And the anti-pattern this framing fights:

> "projects demand plans, but complex projects lure us into creating complicated plans. Until we have finished executing our plans, we won't have anything useful to show for our efforts."
>
> — same URL

Implication: ship the first thin pass of each quadrant as soon as it is usable. Grow each quadrant independently. Do not wait to ship a "complete" docs site that never arrives.

## GitLab levels of edit

GitLab triages review effort instead of applying the same depth to every doc:

> GitLab assigns Technical Writers to stage groups and applies three "levels of edit" (light, medium, heavy) to balance quality against speed.
>
> — https://handbook.gitlab.com/handbook/product/ux/technical-writing/

Implication for maintenance: not every doc warrants the same review cadence. Mission-critical docs get heavy edits; ephemeral ones get light.

## Essentials every project ships

Before worrying about rot, ship a baseline. Write the Docs lists the minimum:

> Essentials every project should ship: *what problem it solves, small code example, link to code and issue tracker, how to get support, how to contribute, install instructions, license.*
>
> — https://www.writethedocs.org/guide/writing/beginners-guide-to-docs/

And know the audience:

> Users — want to use your code and don't care how it works. Developers — want to contribute to your code.
>
> — same URL

## Last-verified stamps (practitioner pattern, not doctrine)

Some teams stamp each doc with a `Last verified: YYYY-MM-DD` line. The research underlying this skill did not find a single primary source prescribing this as doctrine; it is consistent with the Scribelet external-claim-drift quote but is not directly stated there. Treat it as a practitioner pattern, not a cited rule. If the project already stamps, maintain the pattern; if not, do not introduce it as a rule.

## Agent instructions

1. Apply Scribelet's three mitigations together (link check, external-claim verification, owner) rather than picking one.
2. For existing projects, triage docs by GitLab's light/medium/heavy levels before committing to a review cadence.
3. Use `scripts/check-doc-links.sh` to gate PRs on dead links.
4. For external-claim verification, re-fetch the cited URL with WebFetch or Tavily and confirm the quoted text still appears in the source.
5. If the project has no named owner for a doc, assigning one is the highest-leverage rot intervention.
6. Cite https://www.knowledgeowl.com/blog/posts/always-complete-never-finished when recommending publish-early-and-often; that is the attributable source here.
