# Web Search

A request to look something up sends you to the live web. Files on disk answer
a different question. This rule loads every turn and picks the search tool
that fits.

SearchTools {
  Applies { always, loaded on every turn }

  LookItUp {
    (the user says "look it up", "look this up", "verify this",
      "check this", or anything equivalent) => search the live web
      // reading local source, package files, or installed library code
      // answers a different question and leaves the request unmet
    Constraints {
      files on disk carry no authority over upstream behavior, current APIs,
        or documented arguments
        // a vendored copy records what someone installed once, never what
        // a project ships now
    }
  }

  fn choose(question) {
    prefer a purpose-built web research tool over a general fetch or search
      tool
      // fall back on the environment's general capability only where
      // nothing purpose-built exists
    match (what the question needs) {
      case (a fact or a citation)                     => one search
      case (you already hold the URL)                 => extract directly
      case (several sources and citations must stand) => multi-source synthesis
    }
  }

  Constraints {
    omit years from search queries unless the user supplies one
  }
}
