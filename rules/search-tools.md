# Looking things up

This applies when the user says "look it up", "look this up", "verify this", "check this", or anything equivalent. It also applies when about to write a call, flag, or config key against a package the lockfile resolves, and when a tool call just failed.

```sudolang
Constraints {
  search the live web; no local source, package file, or installed library stands in,
    since a copy on disk records what someone installed once
  omit years from queries unless the user supplies one
  cite each source relied on by URL
}

searchTool = first the session exposes of [tvly, linkup]
a library, framework, SDK, or CLI's documentation => context7 before searchTool,
  since it indexes documentation by library and version
chosen tool errors => fall to the next, name which answered
nothing usable => halt, report to the user

beforeFirstCallAgainstResolvedPackage {
  read the current documentation for the resolved version;
    no recollection of the interface stands in for that read
  resolved version postdates your recall => every remembered signature is a guess
    until the read confirms it
}
```

## A failure buys a lookup

```sudolang
onToolFailure {
  stop and read the error before choosing what to do next
  never retry from the recollection that produced the failure,
    since a failure against an interface reports a wrong model of that interface
  match {
    the error names its own fix (linter replacement, compiler suggestion,
      usage line) => apply what it names, skip the lookup
    the error is the red step you predicted => say so in one clause,
      carry on to the code that makes it pass
    second failure, no success between => search the error text verbatim first
    default => run the lookup, resume from what it returns
  }
}

fn lookup {
  name the interface and the version the lockfile resolves
  issue both in one response, neither waiting: {
    read the installed artifact for what the resolved version does:
      its types, its --help output, its bundled documentation
    search the live web for what the package documents now,
      and for the version the docs describe
  }
  they disagree => follow the installed artifact for behavior, name the disagreement,
    give the version each source describes
  close stating what the sources settled and what they left open
}
```

## What a citation rests on

Place each source on a rung before citing it, and cite from the highest rung the lookup reached, since a URL on its own grants a claim nothing.

```sudolang
Source = Artifact | Publisher | Measured | Practitioner | Hearsay
Artifact: the thing itself: the source code, the spec or RFC, the installed package's
  types and --help output, a run and the output it printed
Publisher: the maintainer's own words for the named version: the official documentation,
  the repository's README, changelog, release notes, and issue tracker
Measured: a method a reader can rerun with its data shown: a paper, a benchmark,
  a standards body's test suite
Practitioner: a named author's account carrying something a reader can open: code that
  ran, a reproduced failure, a stated version and date
Hearsay: a source carrying none of the above: a forum answer, a vendor's marketing page,
  an aggregator, a mirror, an unsigned or undated page, a model's output

cite(claim) {
  cite the highest rung reached by URL or path:line, and name the rung in the same
    sentence where it sits below Publisher
  a source citing nothing a reader can open => Hearsay, whatever its publisher
  Hearsay => a lead toward a higher rung, never the citation; no higher rung reached =>
    the claim keeps its mark
  a number => the measurement it came from, never a page that repeats it
  two rungs disagree => the higher holds; name the disagreement and the version
    each describes
}
```
