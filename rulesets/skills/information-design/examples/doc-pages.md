# Worked examples: doc pages

Each example shows a before, an after, and the lesson applied. The instructions are in `references/doc-pages.md`. A full page pair sits in `examples/samples/page.before.md` and `examples/samples/page.after.md`; run `scripts/lint_doc_page.py` on both to see the difference.

## 1. Background first becomes the point first

Before:

```markdown
# Rate limiting

Over the years our API has grown considerably, and with that growth came the need to
protect shared infrastructure. After evaluating several approaches, the platform team
settled on a token bucket...
```

After:

```markdown
# Rate limits

Each API key may make 100 requests per window. Past that, the API answers `429` with a
`Retry-After` header saying how long to wait. This page lists the limits per plan and
shows how to handle a `429`.
```

Lesson: put the answer in the first sentences. A reader who stops after the opening has the limit, the symptom and what the page offers.

## 2. Vague headings become a contents list

Before:

```markdown
## Overview
## Details
## More information
## Notes
```

After:

```markdown
## Limits per plan
## Handle a 429 response
## Request a higher limit
## How the limit is counted
```

Lesson: each heading names what its section holds, in the reader's words, with the distinguishing words first. Read alone, the headings tell a reader where their answer is.

## 3. A paragraph of steps becomes numbered steps

Before:

```markdown
To rotate the key you first need to create a new key in the console, after which you
should update the secret in your deployment (making sure the old key is still active,
otherwise requests will fail), then deploy, and once you've verified traffic is using
the new key, the old one can be revoked.
```

After:

```markdown
1. Create a new key in the console. Leave the old key active.
2. Replace the secret in your deployment with the new key.
3. Deploy.
4. Confirm that requests use the new key: the console shows a "last used" entry for it.
5. Revoke the old key.
```

Lesson: a procedure is numbered steps, one action each, verb first, with the warning placed at the step it concerns and the check placed after the step that produces it.

## 4. Parallel prose becomes a table

Before:

```markdown
The Free plan allows 100 requests and 1 project. On Team you get 1,000 requests, and
you can have up to 10 projects, plus SSO. Enterprise has custom request limits,
unlimited projects, and includes SSO as well as audit logs.
```

After:

```markdown
| | Free | Team | Enterprise |
| --- | ---: | ---: | ---: |
| Requests per window | 100 | 1,000 | custom |
| Projects | 1 | 10 | unlimited |
| SSO | no | yes | yes |
| Audit logs | no | no | yes |
```

Lesson: parallel facts about parallel things go in a grid. The reader compares down a column and across a row, and a missing value becomes visible.

## 5. A list that should have stayed prose

Before:

```markdown
- Caching is enabled
- Stale data
- Invalidate on write
- Performance
```

After:

```markdown
Caching is enabled by default because most reads repeat. The cost is that a read can
return stale data, so every write invalidates the entries it affects.
```

Lesson: a cause, a cost and a consequence are joined by "because" and "so". A list drops those words, and with them the meaning. Use bullets for parallel items and sentences for reasoning.

## 6. Nested conditions become a decision table

Before:

```markdown
If the user is an admin they can delete any project, unless the project is archived,
in which case only owners can, although if the workspace has legal hold then nobody can
delete, except that owners can still archive.
```

After:

```markdown
The first matching row applies.

| Legal hold | Project archived | Role | May delete |
| --- | --- | --- | --- |
| yes | any | any | no |
| no | yes | owner | yes |
| no | yes | any other | no |
| no | no | owner or admin | yes |
| no | no | any other | no |
```

Lesson: when the outcome depends on a combination of conditions, the reader wants to find their row. State the matching order and end with a row for every other case.

## 7. One page with two jobs becomes two pages

Before:

```markdown
# Webhooks

(A page that explains what webhooks are and why they exist, then walks through setup,
then lists every event type and payload field, in one scroll.)
```

After:

```markdown
# Receive your first webhook          (how-to: one task, numbered steps)
# Webhook events and payloads         (reference: one table per event)
# How webhook delivery works          (explanation: retries, ordering, signatures)
```

Lesson: a page has one job. The reader doing a task, the reader looking up a field and the reader wanting to understand each get a page shaped for them, linked to the others.

## 8. Everything shown becomes the common path with detail one step away

Before:

```markdown
## Install

Run the installer. On Windows with a proxy and a custom certificate store, first set...
(Twelve paragraphs of platform and proxy variants precede the one command most readers need.)
```

After:

```markdown
## Install

    curl -fsSL https://example.com/install.sh | sh

Then run `tool --version` to confirm.

<details>
<summary>Install behind a proxy or with a custom certificate store</summary>

...

</details>

<details>
<summary>Install on Windows</summary>

...

</details>
```

Lesson: the main flow holds what most readers need. Rare cases sit behind labels that say exactly who needs them. Nothing needed for safety is hidden.

## 9. "Click here" becomes link text that names the target

Before:

```markdown
For the list of error codes click [here](errors.md). More info is [here](limits.md).
```

After:

```markdown
See the [list of error codes](errors.md) and the [limits per plan](limits.md).
```

Lesson: link text names its destination. A reader scanning links, or hearing them read out as a list, can tell them apart.
