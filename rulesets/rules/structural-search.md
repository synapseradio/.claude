<!-- rule: structural-search -->

## structural-search

For every code search that turns on syntax, a construct, a call form, a declaration form, or a nesting relation, every ast-grep rule you write, test, or debug, and every source file you are about to read whole, optimize for a search whose result means what it says.

`dump_syntax_tree` prints the AST of a snippet. `test_match_code_rule` runs a YAML rule against a snippet. `find_code` searches the codebase by pattern. `find_code_by_rule` searches the codebase by YAML rule.

search
  | the user asks for plain text, or the target sits in a comment, a string, or a filename
      = a text search
  | the query has more than one condition
      = a YAML rule, developed as below, in place of stacked flags
  | the answer depends on how the code parses
      = `ast-grep --lang $language -p '$pattern'`, where `$VAR` matches one node and `$$$` a sequence

About to read a source file whole ? run `ast-grep outline` first.
The outline names the region ? read that region whole.

### Developing a rule

Break the query into the smallest parts that each match one thing, name a sub rule for each, and combine them under a relational or composite rule, on this skeleton.

```yaml
id: [the rule name]
language: [the language]
utils:
  [sub-rule-name]:
    pattern: [the smallest part that matches one thing]
rule:
  all:
    - matches: [sub-rule-name]
    - inside:
        kind: [the enclosing node kind]
        stopBy: end
```

Dump the syntax tree of an example the rule must match -> test against that example.
It matches ? run across the codebase : drop sub rules until it matches, repair the failed part, and test again.
A relational rule comes back empty ? set `stopBy: end` and test again.
A pattern comes back empty twice ? dump the target's syntax tree and rewrite against the node kinds it reports.
Report an empty result as absence only after the rule matched an example.
