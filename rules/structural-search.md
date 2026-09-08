<rule name="structural-search">

  <applies_when>
    A code search turns on syntax: a construct, a call form, a declaration form, a nesting relation. The same holds when you write, test, or debug an ast-grep rule, or are about to read a source file whole.
  </applies_when>

  <optimize_for>
    a search whose result means what it says.
    <why_it_matters>
      An empty result from a rule that matches nothing looks the same as an empty result from a codebase holding nothing, and nothing in the result tells the two apart. A text search over syntax matches strings and comments the parser would skip. The outline prints imports, functions, classes, and direct members with line numbers at a fraction of a whole file's cost, so valuable attention goes to the region the question names.
    </why_it_matters>
  </optimize_for>

  <define name="tools">
    `dump_syntax_tree` prints the AST of a snippet. `test_match_code_rule` runs a YAML rule against a snippet. `find_code` searches the codebase by pattern. `find_code_by_rule` searches the codebase by YAML rule.
  </define>

  <decide name="search">
    Where the user asks for plain text, or the target sits in a comment, a string, or a filename, run a text search. Where the query has more than one condition, develop a YAML rule by the procedure below, with no stacking of flags. Where the answer depends on how the code parses, run `ast-grep --lang $language -p '$pattern'`, where `$VAR` matches one node and `$$$` a sequence.
  </decide>

  <do name="read source">
    Run `ast-grep outline` first. Where the outline names the region, read that region whole.
  </do>

  <do name="develop rule">
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

    Dump the syntax tree of an example the rule must match, and test against that example. Where it matches, run across the codebase. Where it misses, drop sub rules until it matches, repair the failed part, and test again. Where a relational rule finds nothing, set stopBy: end and test again. Where a pattern finds nothing twice, dump the target's syntax tree and rewrite against the node kinds it reports.
  </do>

  <require>
    Run a rule across a codebase only after it matches an example snippet.
  </require>

</rule>
