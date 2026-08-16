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

  constraint SearchToolBan {
    require you never search through the built-in WebSearch tool
    require you never search through mcp__web-search-prime__web_search_prime
      or any other Z.ai web search tool
    (a live-web search is due) => search through the Tavily, linkup, or
      crawl4ai tools
  }
}
