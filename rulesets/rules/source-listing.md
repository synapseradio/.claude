## source-listing

For every search result that names where answers live in files on this machine or pages on the web, optimize for a listing the caller opens and checks entry by entry, the most direct answer first.

- entry: one file or one range of its lines or one web page, listed on its own

### Entries

List each file or page as its own entry.
List only pages this search fetched.

A file's entry holds:

- its path
- for a place inside one file, a line range or a quoted line from it
- one sentence stating what the file's own text says and which reading it answers, quoting the file wherever a quote fits

A web page's entry holds:

- its URL
- an anchor, a heading or a quoted line the caller finds on the page
- the same sentence on the page's own text
- the version or date the page states for itself, with the date of the fetch

file
  | it exists both in the tree's own source and in a copy such as a vendored directory = list the source

### Order

List first the entries that answer a reading most directly.
In a local tree list a decision record, a spec, or a test stating an invariant before one more implementation of the same thing.
On the web, among pages that answer a reading equally directly, list the maintainer's own docs or repository or changelog > a vendor's article > a forum answer > a mirror.
List a page naming its version before an undated one.
Report each entry separately.

conclusion
  | the caller asked for one = state it first, the entries beneath it as its evidence
  | otherwise = leave joining the entries to the caller
