# Remembering across sessions

This applies when the user asks you to remember something, or you identify a fact worth keeping across sessions.

We value a fact that the next session's search finds. A fact in the wrong store sits outside every later search for it, so an unsettled destination gets asked, and nothing gets written until the answer.

```sudolang
route = fact => match (fact) {
  case belongs to one repository => the file memory the harness names in its Memory
    section, naming the repository inside the entry
  case session narrative, a working note, a run file =>
    "scratchpad/$branch/$slug__$DD-MM-YY-HHmm.md"
  default => ask the user which store, write nothing until they answer
}
```
