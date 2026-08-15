# Web Search

A request to look something up sends you to the live web. Files on disk answer
a different question. This rule loads every turn and carries the trigger; the
mechanics of searching, fetching, and caching live with the agent whose
description claims the web as its territory.

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

  Constraints {
    omit years from search queries unless the user supplies one
    (the session holds an agent whose description claims the open web) =>
      the search runs through a spawn of that agent, and its map carries
      the sources
      // tool choice, fallbacks, and the fetch cache live in that agent's
      // body, so this rule stays a trigger
  }
}
