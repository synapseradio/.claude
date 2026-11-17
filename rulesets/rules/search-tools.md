## search-tools

For every lookup and every Jira or Notion read and write, optimize for an answer the reader can trace to the highest source the lookup reached.

- lookup: one the user asked for, one before writing against a package the lockfile resolves, or one after a failed tool call

### The lookup

Read documentation at the version the lockfile resolves.
Put a year in a query only where the user supplies one.

online lookup
  | the tvly CLI (Tavily's command line) is available = use it first in each of its modes, documentation lookups included
  | otherwise = use the linkup MCP tools

tool call
  | it fails = read the error before choosing the next step, and treat the recollection that produced the call as no ground for a retry

### Jira and Notion

Read and write Jira through `acli jira` in Bash, in place of the Atlassian MCP tools.
Read `acli jira <command> --help` for flags before a write.
Read and write Notion through the `ntn` CLI, in place of the Notion MCP and new SDK scripts, and keep using an existing SDK script that works.
Run `ntn` as a direct Bash command, in place of a wrapping shell.
Hold `ntn`'s reach as the pages shared with its integration, and treat its miss as no evidence of absence.

### A documentation site

Before fetching a page from a documentation site by any tool, a package's reference pages included, run `curl -sfL "$origin/llms.txt"` in Bash with `$origin` the URL's scheme and host.
Fetch llms.txt and llms-full.txt only through a direct curl call.

docs
  | the task needs the whole docs set = save `curl -sfL "$origin/llms-full.txt"` to the branch's scratchpad directory and read it by line range, in place of reading it into context whole
  | the index lists a page that answers the question = scrape that page
  | otherwise = scrape the page as usual

scraped page
  | it arrives garbled = fetch it with curl instead

### The source ladder

The rungs run highest first.
Artifact is the code or the spec itself, installed types and `--help` and run output included.
Publisher is what the maintainer publishes for the version, its issues included.
Measured is a method a reader can rerun with its data shown.
Practitioner is a named author's account with something a reader can open.
Hearsay is every other source, whatever its publisher.

Place each source on a rung before citing it.
Cite the highest rung reached by URL or path, naming the rung in the same sentence where it sits below publisher.
Take hearsay as a lead toward a higher rung, and keep it out of every citation.
Cite a number to the measurement it came from, in place of a page that repeats it.

rungs
  | two disagree = follow the higher, and name the disagreement and each version
