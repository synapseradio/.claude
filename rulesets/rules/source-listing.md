## source-listing

For every search result that names where answers live, files on this machine or pages on the web, optimize for a listing the caller opens and checks entry by entry, the most direct answer first.

- entry: one file, one range of lines in a file, or one web page, listed on its own

### Entries

List each file or page as its own entry.
Give a file's entry its path; for a place inside one file, a line range or a quoted line from it; and one sentence stating what the file's own text says and which reading it answers, quoting the file wherever a quote fits.
Give a web page's entry its URL; an anchor, a heading or a quoted line the caller finds on the page; one sentence stating what the page's own text says and which reading it answers, quoting the page wherever a quote fits; and the version or date the page states for itself, with the date of the fetch.
List only pages this search fetched.
A file exists both in the tree's own source and in a copy, a cache, a build output, or a vendored directory for one ? list the source.

### Order

List first the entries that answer a reading most directly.
In a local tree, list a decision record, a spec, or a test stating an invariant before one more implementation of the same thing.
On the web, among pages that answer a reading equally directly, list the maintainer's own docs, repository, or changelog before a vendor's article, an article before a forum answer, a forum answer before a mirror, and a page naming its version before an undated one.
Report each entry separately.
The caller asked for a conclusion ? state it first, the entries beneath it as its evidence : leave their join into a sequence, an order of precedence, or an answer to the caller.
