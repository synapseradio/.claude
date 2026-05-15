# Web Search & External Tools

Always applies. Loaded on every turn.

## "Look it up" means online search

When the user says "look it up", "look this up", "verify this", "check this", or any equivalent phrasing, they mean **search the live web with the Tavily skills**. They do not mean read local source, package files, or installed library code.

Reading source on disk is not looking it up. Local files are not authoritative for upstream behavior, current APIs, or documented kwargs. If the user told you to look it up, open Tavily and search.

Preferred Tavily skills, in order:

- `tavily-search` for a quick fact or citation.
- `tavily-extract` when you already have the URL and want clean content.
- `tavily-research` for multi-source synthesis with citations.

Only fall back to `WebSearch` or `WebFetch` when a Tavily skill is unavailable in this environment.

## Other rules

- Do not include years in search queries unless the user provides one.
- When a specialized search tool is available, use it instead of `WebSearch` or `WebFetch`.
