# Searching code by structure

This applies when a code search turns on syntax: a construct, a call form, a declaration form, a nesting relation. It also applies when writing, testing, or debugging an ast-grep rule, and when about to read a source file whole.

```sudolang
Constraints {
  search through `ast-grep --lang $language -p '$pattern'` wherever the answer depends
    on how the code parses; text search only where the user asks for plain text
    or the target sits in a comment, a string, or a filename
  $VAR matches one node, $$$ a sequence
  more than one condition => a YAML rule via developRule, no stacking of flags
  before reading a source file whole, run `ast-grep outline`, since the outline prints
    imports, functions, classes, and direct members with line numbers at a fraction
    of the file's cost; read whole once the outline names the region
}

Tools {
  dump_syntax_tree: prints the AST of a snippet
  test_match_code_rule: runs a YAML rule against a snippet
  find_code: searches the codebase by pattern
  find_code_by_rule: searches the codebase by YAML rule
}

fn developRule {
  break the query into the smallest parts that each match one thing,
    name a sub rule for each, combine under a relational or composite rule
  dump the syntax tree of an example the rule must match
  test against that example:
    matches => run across the codebase
    misses => drop sub rules until it matches, repair the failed part, test again
  require every rule matches an example snippet before running across a codebase,
    since a rule matching nothing returns the same empty result
    as a codebase holding nothing
  relational rule finds nothing => set stopBy: end, test again
  pattern finds nothing twice => dump the target's syntax tree,
    rewrite against the node kinds it reports
}
```
