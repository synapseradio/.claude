<!-- rule: search-tools -->

## search-tools

For every lookup, one the user asked for in words like "look it up", one that comes before writing a call, flag, or config key against a package the lockfile resolves, or one that follows a failed tool call, optimize for an answer the reader can trace to the highest source the lookup reached.

### The lookup

Where the question is a library, framework, SDK, or CLI's documentation, go to context7 first. Read documentation at the version the lockfile resolves. Where the tvly CLI, the command line for the Tavily service, is unavailable, use the linkup MCP tools. Otherwise, use the tvly CLI for search, extraction, crawling, and research.

Put a year in a query only where the user supplies one. When a tool call failed, read the error before choosing what to do next. Treat the recollection that produced the failed call as no ground for a retry.

### The source ladder

The rungs run highest first. Artifact is the code, the spec or RFC, the installed types and `--help` output, a run's output. Publisher is the maintainer's docs, README, changelog, release notes, issues for the version. Measured is a method a reader can rerun with its data shown. Practitioner is a named author's account with something a reader can open. Hearsay is every source outside the four rungs above, whatever its publisher.

Place each source on a rung before citing it. Cite the highest rung reached by URL or path, naming the rung in the same sentence where it sits below publisher. Take hearsay as a lead toward a higher rung, and keep it out of every citation. Cite a number to the measurement it came from, in place of a page that repeats it. Where two rungs disagree, follow the higher, and name the disagreement and each version.
