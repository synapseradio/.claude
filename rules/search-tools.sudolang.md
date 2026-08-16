SearchTools {
  Applies { the user says "look it up", "look this up", "verify this",
            "check this", or anything equivalent }

  constraint TheLiveWebAnswers {
    search the live web, and let no local source, package file, or
      installed library code stand in for it, since a copy on disk records
      what someone installed once and nothing about upstream now
    omit years from search queries unless the user supplies one
    cite each source you rely on by URL
  }
}
