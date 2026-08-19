StructuralSearch {
  AppliesWhen { a code search turns on syntax rather than text: a construct,
            a call shape, a declaration form, a nesting relation
            | writing, testing, or debugging an ast-grep rule
            | about to read a source file whole }

  constraint SearchTheSyntax {
    search through `ast-grep --lang $language -p '$pattern'` wherever the
      answer depends on how the code parses, and reach for a text search
      only where the user asks for plain text or the target sits in a
      comment, a string, or a filename
    write `$VAR` for one node and `$$$` for a sequence of them
    (the pattern needs more than one condition) => write a YAML rule in
      place of stacking flags   via(developTheRule)
  }

  constraint MapBeforeReading {
    AppliesWhen { about to read a source file whole }
    run `ast-grep outline` on the file first, since it prints imports,
      functions, classes, and their direct members with line numbers at a
      fraction of what the file costs to read
    read the whole file once the outline names the region you need
  }

  Tools {
    dump_syntax_tree     { print the AST of a code snippet }
    test_match_code_rule { run a YAML rule against a snippet }
    find_code            { search the codebase by pattern }
    find_code_by_rule    { search the codebase by YAML rule }
  }

  fn developTheRule(query) {
    break the query into the smallest parts that each match one thing
      |> name a sub rule for each part
      |> combine the sub rules under a relational or composite rule
      |> dump the syntax tree of an example the rule must match
      |> test the rule against that example
      |> match (the outcome) {
           case (it matches) => run it across the codebase
           case (it misses) => drop sub rules until it matches, repair the
             part that failed, and test again
         }
  }

  constraint ProveTheRuleFirst {
    require every rule matches an example snippet before it runs across a
      codebase, since a rule matching nothing returns the same empty result
      as a codebase holding nothing
    (a relational rule finds nothing) => set `stopBy: end` and test again
    (a pattern finds nothing twice) => dump the syntax tree of the target
      code, and rewrite the pattern against the node kinds it reports
  }
}
