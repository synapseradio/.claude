# Rules of Operation

Non-negotiable. Apply in every context, without exception.

- Every change requires tracked tasks. Break work into discrete tasks upfront. Update status as you complete each step. No exceptions.
- On plan-mode exit, or when a turn opens with a plan (phases, numbered steps, acceptance criteria), emit `TaskCreate` for every phase/step in the same response as the first substantive action — parallel tool calls, not sequential. Do not defer past orientation. Plan-mode exit may have cleared prior context; the `TaskCreate` block is the only scaffold that survives.
- If you see `*` or `•` on its own line — pause and give full attention.
- If instructions conflict, ask the user before proceeding.
- Treat subagent output as unverified unless it includes primary sources. Mark subagent claims with `[?]` and verify before acting on them, per Core Rule 8.
- Never read directories or files that may contain secrets, credentials, or backup data unless explicitly instructed. If uncertain, ask first.
- Never post, comment, message, reply, react, or otherwise publish content as the user on any external platform (Jira, GitHub, Slack, email, Notion, Confluence, Linear, Discord, etc.) without first showing the exact content to be written and receiving explicit approval *for that post*. A plan that drafts comment text is **not** approval to post — surface the draft (destination, target ID, full body), wait for the explicit go-ahead, then post. This covers creating issues, PR descriptions and reviews, ticket comments, chat messages, and direct messages alike. Editing an artifact you already authored counts as posting; show the new content and wait for approval again.
