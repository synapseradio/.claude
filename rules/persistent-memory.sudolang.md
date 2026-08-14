# Persistent Memory

A fact worth keeping past the end of a session goes to the store its scope
picks: a repository's file memory, the journal the environment provides, or
the scratchpad. Where the scope stays ambiguous, the user picks.

PersistentMemory {
  Applies { the user asks you to remember something, or you identify
            a fact worth persisting across sessions }

  pick the store by scope, never by convenience
  match (the fact) {
    case (it belongs to one repository) =>
      the file memory the harness names in its Memory section, with the
      repository named inside the entry
      // the store may span projects. the entry carries its own scope
    case (it is session narrative) =>
      whatever journal the environment provides
      // the running account of what happened and why
    case (it is a working note or a run file) =>
      write it where Scratchpad says
  }

  when the scope boundary stays ambiguous, ask the user which store
  require you write nothing until they answer
    // picking one silently buries the fact where nobody goes looking for it
}
