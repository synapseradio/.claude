# Looking things up

This applies when the user says "look it up", "look this up", "verify this", "check this", or anything equivalent. It also applies when about to write a call, flag, or config key against a package the lockfile resolves, and when a tool call just failed.

Search the live web, and let no local source, package file, or installed library code stand in for it, since a copy on disk records what someone installed once. Omit years from search queries unless the user supplies one. Cite each source you rely on by URL.

Search through the first of these the session exposes: tvly, linkup, firecrawl. When the chosen tool errors, fall to the next, and name which tool answered. When the tools return nothing usable, halt and report to the user.

Before the first call against a package the lockfile resolves, read the current documentation for the resolved version, and let no recollection of the interface stand in for that read. When the resolved version postdates what you recall of the package, treat every signature you remember as a guess until the read confirms it.

## A failure buys a lookup

When a tool call just failed, stop and read the error before choosing what to do next. Never attempt again from the recollection that produced the failure, since a failure against an interface reports a wrong model of that interface. Then choose among three paths. When the error names its own fix, as a linter rule carrying its replacement, a compiler suggestion, or a usage line does, apply what it names and skip the lookup. When the error is the red step you predicted before writing the code, say so in one clause and carry on to the code that makes it pass. Otherwise run the lookup and resume from what it returns. When a second failure follows with no success between, search the error text verbatim before anything else.

A lookup names the interface in question and the version the lockfile resolves, then issues the installed-artifact read and the live-web search in one response, letting neither wait on the other. Read the installed artifact for what the resolved version does: its types, its `--help` output, its bundled documentation. Read the live web for what the package documents now, and for the version the docs describe. When the two disagree, follow the installed artifact for behavior, name the disagreement to the user, and give the version each source describes. Close by stating what the sources settled and what they left open.
