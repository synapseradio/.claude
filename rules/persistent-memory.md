# Persistent Memory

Applies when the user asks you to remember something, or you identify a fact worth persisting across sessions.

Two memory systems exist. Pick by scope, not by convenience:

- **Repo-scoped memory** (facts about a specific codebase, project, team, or repo-local workflow): use the per-project auto-memory directory at `~/.claude/projects/<encoded-path>/memory/`, following the types and format described in the auto-memory section of the runtime context.
- **The journal plugin** — use this at the beginning of sessions to start tracking a session in the journal. It is often wise to use `/loop` to spawn a background agent that handles note-taking as the conversation progresses. The Sonnet agent should take notes every 2-3 minutes, and not report back if there is nothing new to write.

If the scope boundary is ambiguous — e.g., a preference that *might* apply only here, or a fact that *might* generalize — ask the user which system to store it in before writing. Do not silently pick.
