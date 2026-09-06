# Reading documentation on the web

This applies when about to scrape, crawl, or extract a page from a documentation site: a docs subdomain, a `/docs` path, a package's reference pages. Which search tool answers a question stays with the rule on looking things up.

We value the page that answers the question, read as its author wrote it. A full llms-full.txt can exceed 300 KB, so it lands in scratchpad and gets read by line range. A scrape tool escapes markdown characters, drops line breaks, and decodes non-ASCII wrong when the server sends no charset, so the index files travel through curl.

```sudolang
fn readDocs(url) {
  origin = scheme and host of url
  index = run `curl -sfL "$origin/llms.txt"` in Bash
  match (index) {
    case absent => scrape the page as usual
    case present => pick the page it lists that answers the question, scrape that page
  }
  the task needs the whole docs set => save `curl -sfL "$origin/llms-full.txt"` to the
    branch's scratchpad directory, read it by line range, never into context whole
  require llms.txt and llms-full.txt travel through curl, never through a scrape tool
}
```
