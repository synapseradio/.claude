<rule name="reading-docs">

<applies_when>You are about to scrape, crawl, or extract a page from a documentation site: a docs subdomain, a `/docs` path, a package's reference pages. Which search tool answers a question stays with the rule on looking things up.</applies_when>

<optimize_for>
the page that answers the question, read as its author wrote it.
<why_it_matters>A site that publishes llms.txt names its pages for exactly this reading, and the page it lists that answers the question tends to cost less than a crawl. A full llms-full.txt can exceed 300 KB, more than a context should carry whole. A scrape tool escapes markdown characters, drops line breaks, and decodes non-ASCII wrong when the server sends no charset, and curl carries the bytes as the server sent them.</why_it_matters>
</optimize_for>

<do name="read docs">
Take the origin of the URL, the scheme and host, and run `curl -sfL "$origin/llms.txt"` in Bash. Where the index is absent, scrape the page as usual. Where it is present, pick the page it lists that answers the question, and scrape that page. Where the task needs the whole docs set, save `curl -sfL "$origin/llms-full.txt"` to the branch's scratchpad directory and read it by line range, never into context whole.
</do>

<require>
The llms.txt and llms-full.txt files travel through curl, never through a scrape tool.
</require>

</rule>
