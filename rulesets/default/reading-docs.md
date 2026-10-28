<!-- rule: reading-docs -->

## reading-docs

For every page you scrape, crawl, or extract from a documentation site, a docs subdomain, a `/docs` path, or a package's reference pages, optimize for the page that answers the question, read as its author wrote it.

Run `curl -sfL "$origin/llms.txt"` in Bash, with `$origin` the URL's scheme and host.
The index is absent ? scrape the page as usual : scrape the page it lists that answers the question.
The task needs the whole docs set ? save `curl -sfL "$origin/llms-full.txt"` to the branch's scratchpad directory and read it by line range, in place of reading it into context whole.
Fetch llms.txt and llms-full.txt only through a direct curl call.
A scraped page arrives with escaped markdown, lost line breaks, or wrong characters ? fetch it with curl instead.
