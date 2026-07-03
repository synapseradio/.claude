# Persistent Memory

Applies when the user asks you to remember something, or you identify a fact worth persisting across sessions.

Two memory systems exist. Pick by scope, not by convenience:

- **Repo-scoped memory**: use the per-project file memory the harness specifies in its Memory section.
- **The journal plugin**: use this at the beginning of sessions to start tracking a session in the journal. Consider using `/loop` to spawn a background agent that handles note-taking as the conversation progresses. The Sonnet agent should take notes every 2-3 minutes, and not report back when nothing new needs writing.

If the scope boundary remains ambiguous, ask the user which system to store it in before writing. Do not silently pick.
