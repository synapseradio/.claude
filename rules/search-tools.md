# Web Search

Always applies. Loaded on every turn.

## "Look it up" means searching the live web

Search the live web whenever the user says "look it up", "look this up", "verify this",
"check this", or anything equivalent. Reading local source, package files, or installed
library code answers a different question and leaves the request unmet.

Treat files on disk as carrying no authority over upstream behavior, current APIs, or
documented arguments. A vendored copy records what someone installed once, never what a
project ships now.

## Choosing a tool

Prefer a purpose-built web research tool over a general fetch or search tool. Fall back on
whatever general capability the environment offers only where nothing purpose-built exists.

Match the tool to the question. Run one search for a fact or a citation. Extract directly
where you already hold the URL. Reach for multi-source synthesis where an answer needs
several sources and citations to stand.

## Other rules

Omit years from search queries unless the user supplies one.
