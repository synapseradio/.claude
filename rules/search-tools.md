# Web Search

```sudolang
SearchTools {
  Applies { always; loaded on every turn }

  LookItUp {
    "look it up" | "look this up" | "verify this" | "check this" | anything equivalent
      -> search the live web
      // reading local source, package files, or installed library code
      // answers a different question and leaves the request unmet
    files on disk carry no authority over upstream behavior, current APIs,
      or documented arguments
      // a vendored copy records what someone installed once, never what
      // a project ships now
  }

  ChoosingATool {
    prefer a purpose-built web research tool over a general fetch or search tool
      // fall back on the environment's general capability only where
      // nothing purpose-built exists
    match the tool to the question {
      a fact or a citation                     -> one search
      you already hold the URL                 -> extract directly
      several sources and citations must stand -> multi-source synthesis
    }
  }

  omit years from search queries unless the user supplies one
}
```
