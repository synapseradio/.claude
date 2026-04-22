# Sourcing and Citations

Every claim about an external system, API, version, limit, or behaviour needs a resolvable URL. Uncited external claims are the dominant rot vector named in the research underlying this skill.

## Primary sources

| URL | Topic |
|-----|-------|
| https://developers.google.com/style | Google developer style guide — reference hierarchy |
| http://www.catb.org/~esr/writings/taoup/html/ch18s06.html | Raymond — honesty rule (never omit warnings) |
| https://scribelet.app/blog/outdated-documentation | Scribelet — external-claim drift |

## What needs a citation

- API signatures, parameters, return types, and error codes for any external system.
- Version numbers and release dates.
- Rate limits, quota numbers, pricing tiers.
- Vendor-specific behaviour (e.g., "Stripe treats X as Y").
- Named standards (RFC, PEP, W3C specs).
- Style claims ("Google says active voice").

Name-dropping a technology ("we use REST") is not a cite-requiring claim. Quoting a behaviour rule is.

See CLAUDE.md's Core Rule 8 ("Cite or mark") for the general-purpose form of this rule: every backing assertion needs a resolvable source, or ends with `[?]`.

## Google's reference hierarchy

For style questions specifically, Google names a resolution order:

> Reference hierarchy: project-specific style → this guide → third-party references (Merriam-Webster, Chicago Manual, Microsoft Writing Style Guide).
>
> — https://developers.google.com/style

Apply the hierarchy when two style sources disagree. Project style overrides any external source. Where the project is silent, Google's guide is the next fallback.

## Raymond's honesty rule

Citations exist to protect the reader, not decorate the page. Raymond names the failure mode directly:

> "Don't think for a moment that volume will be mistaken for quality. And especially, never ever omit functional details because you fear they might be confusing, nor warnings about problems because you don't want to look bad. It is unanticipated problems that will cost you credibility and users, not the problems you were honest about."
>
> — http://www.catb.org/~esr/writings/taoup/html/ch18s06.html

Never remove a warning or a caveat to tidy a doc. If the underlying system has a sharp edge, the doc names it.

## External-claim drift

Scribelet identifies external-claim drift as the principal failure of long-lived docs:

> "Docs-as-code makes documentation maintainable in principle... Reference docs go stale when external systems they describe ship breaking changes (a dependency, an API, a vendor configuration). A combination [works]: link checkers for dead URLs, AI verification for external-claim drift, and a named owner per doc for everything tooling can't catch."
>
> — https://scribelet.app/blog/outdated-documentation

Three mitigations combine: link checkers, external-claim verification, and an owner per doc. No single tool is enough.

See `rot-prevention.md` for the full rot playbook.

## Practical citation rules

- Every external-claim sentence ends with a URL.
- URLs point at the primary source, not an aggregator. If the API is documented on Stripe's site, link Stripe — not a blog post that quotes Stripe.
- Dates of verification belong in the maintenance record (see `workflow-maintain.md`), not scattered through prose.
- If no source is reachable, mark the claim `[?]` and drop it from authoritative reference material.

## Agent instructions

1. When drafting, attach the URL to the claim in the same sentence. Separating URLs into a bibliography decouples the claim from its backing and invites drift.
2. When reviewing, scan for external-claim sentences without URLs. Flag each one with the rule citation from Scribelet above.
3. Invoke Raymond's honesty rule (cited above) when the draft omits a known warning, limit, or gotcha.
4. Follow Google's reference hierarchy to resolve style disputes; cite the hierarchy when doing so.
