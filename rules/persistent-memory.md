# Persistent Memory

```sudolang
PersistentMemory {
  Applies { the user asks you to remember something, or you identify
            a fact worth persisting across sessions }

  pick the store by scope, never by convenience {
    fact belonging to one repository -> the file memory the harness names
                                        in its Memory section, the repository
                                        named inside the entry
      // the store may span projects; the entry carries its own scope
    session narrative                -> whatever journal the environment provides
      // the running account of what happened and why
    working notes and run files      -> ./scratchpad.md routes them
  }

  scope boundary stays ambiguous -> ask the user which store,
    and write nothing until they answer
    // picking one silently buries the fact where nobody goes looking for it
}
```
