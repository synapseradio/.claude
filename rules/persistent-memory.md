PersistentMemory {
  AppliesWhen { the user asks you to remember something, or you identify a
            fact worth keeping across sessions }

  fn store(fact) {
    match (fact) {
      case (it belongs to one repository) =>
        write it to the file memory the harness names in its Memory
        section, naming the repository inside the entry
      case (it is session narrative) =>
        write it to the journal the environment provides
      case (it is a working note or a run file) =>
        write it under `scratchpad/`, inside a subdirectory named for the
        current branch when on one, in a file whose name carries a
        timestamp: `scratchpad/$branch/$YYYYMMDD-HHmm-$slug.md`
      default => ask the user which store, and write nothing until they
        answer, since a fact in the wrong store sits outside every later
        search for it
    }
  }
}
