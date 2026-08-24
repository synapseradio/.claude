# Remembering across sessions

This applies when the user asks you to remember something, or you identify a fact worth keeping across sessions.

```sudolang
route(fact) = match {
  belongs to one repository => the file memory the harness names in its Memory
    section, naming the repository inside the entry
  session narrative, a working note, a run file =>
    "scratchpad/$branch/$slug__$DD-MM-YY-HHmm.md"
  default => ask the user which store, write nothing until they answer,
    since a fact in the wrong store sits outside every later search for it
}
```
