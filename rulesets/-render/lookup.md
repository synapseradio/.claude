<!-- rule: search-tools -->
## search-tools

For every lookup, one the user asked for in words like "look it up", one before writing a call, flag, or config key against a package the lockfile resolves, or one after a failed tool call, optimize for an answer the reader can trace to the highest source the lookup reached.

### The lookup

The question is a library, framework, SDK, or CLI's documentation ? go to context7 first.
Read documentation at the version the lockfile resolves.
The tvly CLI, Tavily's command line, is available ? use it for search, extraction, crawling, and research : use the linkup MCP tools.
Put a year in a query only where the user supplies one.
A tool call fails ? read the error before choosing the next step, and treat the recollection that produced the call as no ground for a retry.

### A documentation site

Before scraping, crawling, or extracting a page from a documentation site, a docs subdomain, a `/docs` path, or a package's reference pages, run `curl -sfL "$origin/llms.txt"` in Bash, with `$origin` the URL's scheme and host.
The index lists a page that answers the question ? scrape that page : scrape the page as usual.
The task needs the whole docs set ? save `curl -sfL "$origin/llms-full.txt"` to the branch's scratchpad directory and read it by line range, in place of reading it into context whole.
Fetch llms.txt and llms-full.txt only through a direct curl call.
A scraped page arrives with escaped markdown, lost line breaks, or wrong characters ? fetch it with curl instead.

### The source ladder

The rungs run highest first. Artifact is the code, the spec or RFC, the installed types and `--help` output, a run's output. Publisher is the maintainer's docs, README, changelog, release notes, issues for the version. Measured is a method a reader can rerun with its data shown. Practitioner is a named author's account with something a reader can open. Hearsay is every other source, whatever its publisher.

Place each source on a rung before citing it. Cite the highest rung reached by URL or path, naming the rung in the same sentence where it sits below publisher. Take hearsay as a lead toward a higher rung, and keep it out of every citation. Cite a number to the measurement it came from, in place of a page that repeats it.
Two rungs disagree ? follow the higher, and name the disagreement and each version.

<!-- rule: structural-search -->
## structural-search

For every code search that turns on syntax, a construct, a call form, a declaration form, or a nesting relation, every ast-grep rule you write, test, or debug, and every source file you are about to read whole, optimize for a search whose result means what it says.

`dump_syntax_tree` prints the AST of a snippet. `test_match_code_rule` runs a YAML rule against a snippet. `find_code` searches the codebase by pattern. `find_code_by_rule` searches the codebase by YAML rule.

search
  | the user asks for plain text, or the target sits in a comment, a string, or a filename
      = a text search
  | the query has more than one condition
      = a YAML rule, developed as below, in place of stacked flags
  | the answer depends on how the code parses
      = `ast-grep --lang $language -p '$pattern'`, where `$VAR` matches one node and `$$$` a sequence

About to read a source file whole ? run `ast-grep outline` first.
The outline names the region ? read that region whole.

### Developing a rule

Break the query into the smallest parts that each match one thing, name a sub rule for each, and combine them under a relational or composite rule, on this skeleton.

```yaml
id: [the rule name]
language: [the language]
utils:
  [sub-rule-name]:
    pattern: [the smallest part that matches one thing]
rule:
  all:
    - matches: [sub-rule-name]
    - inside:
        kind: [the enclosing node kind]
        stopBy: end
```

Dump the syntax tree of an example the rule must match -> test against that example.
It matches ? run across the codebase : drop sub rules until it matches, repair the failed part, and test again.
A relational rule comes back empty ? set `stopBy: end` and test again.
A pattern comes back empty twice ? dump the target's syntax tree and rewrite against the node kinds it reports.
Report an empty result as absence only after the rule matched an example.
