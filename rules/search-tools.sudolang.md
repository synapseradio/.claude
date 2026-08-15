# Web Search

A request to look something up sends you to the live web. Files on disk answer
a different question. This rule loads every turn and carries the trigger; the
mechanics of searching, fetching, and caching live with the agent whose
description claims the web as its territory.

SearchTools {
  Applies { always, loaded on every turn }

  LookItUp {
    (the user says "look it up", "look this up", "verify this",
      "check this", or anything equivalent) => search the live web, and let
      no local source, package file, or installed library code stand in for
      that search: each answers a different question and leaves the request
      unmet
    Constraints {
      files on disk carry no authority over upstream behavior, current APIs,
        or documented arguments, since a vendored copy records what someone
        installed once
    }
  }

  Constraints {
    omit years from search queries unless the user supplies one
    (the session holds an agent whose description claims the open web) =>
      the search runs through a spawn of that agent, and its map carries
      the sources, with tool choice, fallbacks, and the fetch cache left
      to that agent
  }
}
