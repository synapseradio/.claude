# Rules of Operation

These hold in every context, and they hold without negotiation.

Multi-step work runs on tracked tasks. Break the work into discrete tasks upfront, and update status as each step completes. A single trivial step proceeds without a task entry.

Emit `TaskCreate` at orientation. When plan mode exits, or when a turn opens with phases, numbered steps, or acceptance criteria, emit `TaskCreate` for every phase in the same response as the first substantive action. Issue the calls in parallel.

A `*` or `•` on its own line invokes the user override. Core Rule 0 in [core-rules.md](./core-rules.md) owns its semantics.

When a user instruction conflicts with your understanding of the task at hand, stop and ask before proceeding. Conflicts you can settle from the rules, the code, or the harness stay yours to settle: choose, act, and say which way you went and why.

Close agent type, model, effort, and prompt before every delegation. [agent-delegation.md](./agent-delegation.md) owns those decisions and how to receive what comes back.

Read directories or files that may hold secrets, credentials, or backup data only on explicit instruction. Where a path's status stays uncertain, ask.

Acting on the user's behalf on any external platform waits for two things: showing the exact content, and receiving explicit approval. Editing content you already authored counts as acting on the user's behalf.
