# Looking things up

This applies when the user says "look it up", "verify this", "check this", or equivalent, when about to write a call, flag, or config key against a package the lockfile resolves, and when a tool call just failed.

We value an answer the reader can trace to the highest source the lookup reached. A URL on its own grants a claim nothing, so each source sits on a rung of the Source ladder before it gets cited. Context7 indexes by library and version, so a library's documentation goes there first. A retry from the recollection that produced a failed call repeats the failure.

```sudolang
lookup = question => match (question) {
  case a library, framework, SDK, or CLI's documentation => context7 first
  case deep research => the linkup MCP tools
  default => the live web through the tvly CLI
}
omit years from queries unless the user supplies one
a tool call failed => read the error before choosing what to do next, never retrying
  from the recollection that produced it

Source {
  rung: Artifact | Publisher | Measured | Practitioner | Hearsay
  Artifact: the code, the spec or RFC, the installed types and --help output, a run's output
  Publisher: the maintainer's docs, README, changelog, release notes, issues for the version
  Measured: a method a reader can rerun with its data shown
  Practitioner: a named author's account with something a reader can open
  Hearsay: none of the above, whatever its publisher
}

fn cite(claim) {
  cite the highest rung reached by URL or path:line, naming the rung in the same
    sentence where it sits below Publisher
  Hearsay => a lead toward a higher rung, never the citation
  a number => the measurement it came from, never a page that repeats it
  two rungs disagree => the higher holds, name the disagreement and each version
}
```
