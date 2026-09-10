<!-- rule: reading-docs -->

## reading-docs

For every page you scrape, crawl, or extract from a documentation site, a docs subdomain, a `/docs` path, or a package's reference pages, optimize for the page that answers the question, read as its author wrote it. Which search tool answers a question stays with the rule on looking things up.

Take the origin of the URL, the scheme and host, and run `curl -sfL "$origin/llms.txt"` in Bash. Where the index is absent, scrape the page as usual. Where it is present, pick the page it lists that answers the question, and scrape that page. Where the task needs the whole docs set, save `curl -sfL "$origin/llms-full.txt"` to the branch's scratchpad directory and read it by line range, never into context whole. Fetch llms.txt and llms-full.txt only through a direct curl call. Where a scraped page arrives with escaped markdown, lost line breaks, or wrong characters, fetch it with curl instead.
