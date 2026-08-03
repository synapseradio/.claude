# Scratchpad

The harness environment section names a session scratchpad directory and asks that all
temporary files go there instead of `/tmp`. That instruction stands. This rule only
redirects where it points.

Inside a git repository, every path the harness gives as the scratchpad directory
resolves to `scratchpad/` at that repository's root. Read the harness instruction as
naming that directory, and write there.

Outside a git repository, the harness path stands exactly as given.

## Setting it up

On first write in a repository, create `scratchpad/` and add `scratchpad/` to that
repository's `.gitignore` in the same action, under a comment naming what lives there.
Both steps happen before the first file lands, so nothing untracked is ever left staged
for a commit.

Write working notes into the plan file while plan mode holds, and create `scratchpad/` on
the first write once writing opens up. A read-only mode suspends both setup steps, since
neither can run there.

Skills and workflows that name their own default, such as a run file at
`/tmp/<skill>-<slug>.md`, redirect the same way: `scratchpad/<skill>-<slug>.md`. Say
once where the file went.

## Why the redirect

A session directory disappears with the session and sits far from the code its notes
describe. A repository-local directory keeps working notes beside the thing they are
about, survives across sessions, and stays reachable by ordinary tools: the user opens
it in their editor, greps it, and reads a review from three weeks ago without knowing a
session id. Gitignoring it keeps that convenience out of history.

## What the redirect covers

Everything the harness instruction already covers: intermediate results, working files,
throwaway scripts, generated data, and any output that does not belong in the user's
project. Reviews, audits, plans, and run files land here too.

It does not cover deliverables. Documentation the project ships belongs in its docs
tree, source belongs in its source tree, and a file the user asked for by name goes
where they named it. Secrets and credentials belong in neither place. Never write into
`scratchpad/` to avoid deciding where a real artifact lives; when you cannot tell
whether output is a deliverable, ask.
