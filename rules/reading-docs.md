# Reading documentation on the web

This applies when about to scrape, crawl, or extract a page from a documentation site: a docs subdomain, a `/docs` path, a package's reference pages. Which search tool answers a question stays with the rule on looking things up.

```sudolang
fn readDocs(url) {
  origin = scheme and host of url
  index = run `curl -sfL "$origin/llms.txt"` in Bash
  index absent => scrape the page as usual
  index present => pick the page it lists that answers the question, scrape that page
  the task needs the whole docs set => save `curl -sfL "$origin/llms-full.txt"`
    to the branch's scratchpad directory, read it by line range,
    never into context whole, since a full file can exceed 300 KB
  read llms.txt and llms-full.txt through curl, never through a scrape tool,
    since the scrape path escapes markdown characters, drops line breaks,
    and decodes non-ASCII wrong when the server sends no charset
}
```
