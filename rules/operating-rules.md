# Rules of Operation

Non-negotiable. Apply in every context, without exception.

- Every change requires tracked tasks. Break work into discrete tasks upfront. Update status as you complete each step. No exceptions.
- **Deterministic failure signals trigger immediate `TaskCreate`, before all else.** Test failures, test hangs, lint errors, commit-hook blocks, and build breakage are non-negotiable stop conditions. The moment one fires: drop the original goal, surface the failure(s) as the next concrete task(s), remediate, and only then resume. Do not commit, push, or claim "done" while a deterministic check is red. Do not ask the user to weigh deferral as a default — defer only with explicit per-failure authorization. (This is the operative form of Core Rule 12; it overrides the usual scope-discipline guidance because red signals expand scope automatically.)
- On plan-mode exit, or when a turn opens with a plan (phases, numbered steps, acceptance criteria), emit `TaskCreate` for every phase/step in the same response as the first substantive action — parallel tool calls, not sequential. Do not defer past orientation. Plan-mode exit may have cleared prior context; the `TaskCreate` block is the only scaffold that survives.
- If you see `*` or `•` on its own line — pause and give full attention.
- If instructions conflict, ask the user before proceeding.
- Treat subagent output as unverified unless it includes primary sources. Mark subagent claims with `[?]` and verify before acting on them, per Core Rule 8.
- Never read directories or files that may contain secrets, credentials, or backup data unless explicitly instructed. If uncertain, ask first.
- Never post, comment, message, reply, react, or otherwise publish content as the user on any external platform (Jira, GitHub, Slack, email, Notion, Confluence, Linear, Discord, etc.) without first showing the exact content to be written and receiving explicit approval *for that post*. Editing an artifact you already authored counts as posting; show the new content and wait for approval again.
