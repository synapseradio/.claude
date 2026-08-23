# Searching code by structure

This applies when a code search turns on syntax: a construct, a call form, a declaration form, a nesting relation. It also applies when writing, testing, or debugging an ast-grep rule, and when about to read a source file whole.

Search through `ast-grep --lang $language -p '$pattern'` wherever the answer depends on how the code parses, and reach for a text search only where the user asks for plain text or the target sits in a comment, a string, or a filename. Write `$VAR` for one node and `$$$` for a sequence of them. When the pattern needs more than one condition, write a YAML rule and develop it as described below, with no stacking of flags.

Before reading a source file whole, run `ast-grep outline` on it, since the outline prints imports, functions, classes, and their direct members with line numbers at a fraction of what the file costs to read. Read the whole file once the outline names the region you need.

Four tools serve this work. `dump_syntax_tree` prints the AST of a code snippet. `test_match_code_rule` runs a YAML rule against a snippet. `find_code` searches the codebase by pattern. `find_code_by_rule` searches the codebase by YAML rule.

Develop a rule by breaking the query into the smallest parts that each match one thing, naming a sub rule for each part, and combining the sub rules under a relational or composite rule. Dump the syntax tree of an example the rule must match, and test the rule against that example. When it matches, run it across the codebase. When it misses, drop sub rules until it matches, repair the part that failed, and test again.

Every rule matches an example snippet before it runs across a codebase, since a rule matching nothing returns the same empty result as a codebase holding nothing. When a relational rule finds nothing, set `stopBy: end` and test again. When a pattern finds nothing twice, dump the syntax tree of the target code, and rewrite the pattern against the node kinds it reports.
