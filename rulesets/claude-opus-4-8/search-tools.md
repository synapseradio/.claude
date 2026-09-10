<!-- rule: search-tools -->

## search-tools

For every lookup, whether the user asked in words like "look it up", "verify this", or "check this", a call, flag, or config key is about to be written against a package the lockfile resolves, or a tool call just failed, optimize for an answer the reader can trace to the highest source the lookup reached.

### The lookup

Where the question is a library, framework, SDK, or CLI's documentation, go to context7 first. Read documentation at the version the lockfile resolves. Where the question calls for deep research, use the linkup MCP tools. Otherwise, search the live web through the tvly CLI.

Omit years from queries unless the user supplies one. When a tool call failed, read the error before choosing what to do next. Never retry from the recollection that produced the failed call.

### The source ladder

The rungs run highest first. Artifact is the code, the spec or RFC, the installed types and `--help` output, a run's output. Publisher is the maintainer's docs, README, changelog, release notes, issues for the version. Measured is a method a reader can rerun with its data shown. Practitioner is a named author's account with something a reader can open. Hearsay is none of the above, whatever its publisher.

Place each source on a rung before citing it. Cite the highest rung reached by URL or path:line, naming the rung in the same sentence where it sits below publisher. Take hearsay as a lead toward a higher rung, never as the citation. Cite a number to the measurement it came from, never to a page that repeats it. Where two rungs disagree, follow the higher, and name the disagreement and each version.
