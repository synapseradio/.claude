# Persistent Memory

Applies when the user asks you to remember something, or you identify a fact worth persisting across sessions.

Two memory systems exist. Pick by scope, not by convenience:

- **Repo-scoped memory**: use the per-project auto-memory directory at `~/.claude/projects/<encoded-path>/memory/`, following the types and format described in the auto-memory section of the runtime context.
- **The journal plugin**: use this at the beginning of sessions to start tracking a session in the journal. Consider using `/loop` to spawn a background agent that handles note-taking as the conversation progresses. The Sonnet agent should take notes every 2-3 minutes, and not report back if there is nothing new to write.

If the scope boundary is ambiguous, ask the user which system to store it in before writing. Do not silently pick.
