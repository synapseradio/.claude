<!-- rule: structural-search -->

## structural-search

For every code search that turns on syntax, a construct, a call form, a declaration form, or a nesting relation, for every ast-grep rule you write, test, or debug, and for every source file you are about to read whole, optimize for a search whose result means what it says.

### The tools

`dump_syntax_tree` prints the AST of a snippet. `test_match_code_rule` runs a YAML rule against a snippet. `find_code` searches the codebase by pattern. `find_code_by_rule` searches the codebase by YAML rule.

### Choosing the search

Where the user asks for plain text, or the target sits in a comment, a string, or a filename, run a text search. Where the query has more than one condition, develop a YAML rule by the procedure below, with no stacking of flags. Where the answer depends on how the code parses, run `ast-grep --lang $language -p '$pattern'`, where `$VAR` matches one node and `$$$` a sequence.

### Reading a source file

Run `ast-grep outline` first. Where the outline names the region, read that region whole.

### Developing a rule

Break the query into the smallest parts that each match one thing, name a sub rule for each, and combine them under a relational or composite rule. This skeleton shows the parts.

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

Dump the syntax tree of an example the rule must match, and test against that example. Where it matches, run across the codebase. Where it misses, drop sub rules until it matches, repair the failed part, and test again. Where a relational rule finds nothing, set `stopBy: end` and test again. Where a pattern finds nothing twice, dump the target's syntax tree and rewrite against the node kinds it reports. Run a rule across a codebase only after it matches an example snippet. Never report an empty result as absence until the rule matched an example.
