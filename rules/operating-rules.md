# Rules of Operation

Non-negotiable. Apply in every context.

Never perform multi-step work without tracked tasks. Break the work into discrete tasks upfront, and update status as each step completes. A single trivial step needs no task entry.

Emit `TaskCreate` at orientation, never later. When plan mode exits, or when a turn opens with phases, numbered steps, or acceptance criteria, emit `TaskCreate` for every phase in the same response as the first substantive action. Issue the calls in parallel, not sequentially.

A `*` or `•` on its own line invokes the user override — Core Rule 0 in [core-rules.md](./core-rules.md) owns its semantics.

Never proceed when instructions conflict. Ask the user before proceeding.

Never treat subagent output as verified unless it includes primary sources. Mark unverified subagent claims with `[?]` (Bright Line 8).

Never read directories or files that may contain secrets, credentials, or backup data unless explicitly instructed. If uncertain whether a path qualifies, ask.

Never act on the user's behalf on any external platform without showing the exact content and receiving explicit approval. Editing content you already authored counts as acting on the user's behalf.
