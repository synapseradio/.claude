# Persistent Memory

A fact worth keeping past the end of a session goes to the store its scope
picks: a repository's file memory, the journal the environment provides, or
the scratchpad. Where the scope stays ambiguous, the user picks.

PersistentMemory {
  Applies { the user asks you to remember something, or you identify
            a fact worth persisting across sessions }

  fn store(fact) {
    pick the store by scope alone
    match (the fact) {
      case (it belongs to one repository) =>
        the file memory the harness names in its Memory section, which may
        span projects, so name the repository inside the entry
      case (it is session narrative) =>
        whatever journal the environment provides, the running account of
        what happened and why
      case (it is a working note or a run file) =>
        write it where Scratchpad says
    }
  }

  (the scope boundary stays ambiguous) => ask the user which store
  require nothing is written until they answer, since a fact written to the
    wrong store sits outside every later search for it
}
