# Searching code by structure

This applies when a code search turns on syntax: a construct, a call form, a declaration form, a nesting relation. It also applies when writing, testing, or debugging an ast-grep rule, and when about to read a source file whole.

We value a search whose result means what it says. A rule that matches nothing returns the same empty result as a codebase holding nothing, so every rule matches an example snippet first. A text search over syntax matches strings and comments the parser would skip. The outline prints imports, functions, classes, and direct members with line numbers at a fraction of a whole file's cost.

```sudolang
Tools {
  dump_syntax_tree: prints the AST of a snippet
  test_match_code_rule: runs a YAML rule against a snippet
  find_code: searches the codebase by pattern
  find_code_by_rule: searches the codebase by YAML rule
}

search = query => match (query) {
  case the user asks for plain text, or the target sits in a comment, a string,
    or a filename => text search
  case more than one condition => a YAML rule through developRule, no stacking of flags
  case the answer depends on how the code parses =>
    `ast-grep --lang $language -p '$pattern'`, where `$VAR` matches one node
    and `$$$` a sequence
}

fn readSource(file) {
  run `ast-grep outline` first
  the outline names the region => read that region whole
}

fn developRule(query) {
  break the query into the smallest parts that each match one thing, name a sub rule
    for each, combine under a relational or composite rule
  dump the syntax tree of an example the rule must match
  test against that example
  match (test) {
    case matches => run across the codebase
    case misses => drop sub rules until it matches, repair the failed part, test again
  }
  a relational rule finds nothing => set stopBy: end, test again
  a pattern finds nothing twice => dump the target's syntax tree, rewrite against
    the node kinds it reports
  require every rule matches an example snippet before running across a codebase
}
```
