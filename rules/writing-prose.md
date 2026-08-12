# Writing Prose

Holds for all prose in all contexts. Value simplicity, clarity, relevance, and precision.

```sudolang
WritingProse {
  Applies { all prose, all contexts; code comments count as prose }
    // this file reaches the sentences inside a comment
    via(./writing-comments.md)  // when a comment exists, and what it carries
  Values = [simplicity, clarity, relevance, precision]

  Never {
    // each of these tells on the writing: readers take it, on sight, as
    // unexamined LLM output. the ban binds absolutely in every register:
    // artifacts, chat replies, comments, commit messages. sweep each
    // message against this list before it leaves, hardest late in a
    // long context, and repair any instance the moment you see it
    em dash                                      // the loudest tell; a casualty
    "shape" as a generic term
    "load-bearing"
    emoji, unless the user asks for one
    TL;DR on a message under 200 words
    virtue verdict on your own work ("honestly", "a rigorous analysis")
                                                 -> GrammarSmuggling.VirtueVerdicts
    definite article on a same-document coinage ("the" on first mention of a term coined in the same document)
                                                 -> GrammarSmuggling.CoinedTerms
    negation-affirmation mirror ("X is Y, not Z" | "not just Y but Z")
                                                 -> GrammarSmuggling.Mirrors
    abstraction verbing an abstraction ("the rubric carries the process")
                                                 -> GrammarSmuggling.AbstractActors
    semicolon joining clauses                    // the same tell, quieter
  }

  GrammarSmuggling {
    // content encoded in grammar never presents itself as a claim, so it lands
    // unexamined whether or not it holds. each pattern below rides in without
    // asking whoever reads to weigh it. state the claim outright and let the
    // reader weigh it.
    //
    // strength: nodes Never points at bind absolutely. the rest hold as
    // defaults. depart deliberately, and say what the departure does for
    // the reader.

    ExistencePredicates {
      spot   { "The __ is real." | "The opportunity is the signal." }
      why    { mentioning a thing already presupposes it exists; the predicate
               performs emphasis where it should supply it }
      repair { state what the thing indicates and how that indication works }
    }

    Mirrors {
      spot   { comma form: "X is Y, not Z" | dash form: "It is not Y, it's Z"
             | "not just Y but Z"
             | verb swap across sentences: "It did not dissolve X. It contained X." }
      repair { lead with the affirmative; the negated half goes unwritten }
      invited { a negation some specific party asserted -> name them and give it
               a full clause of its own }
    }

    LinkingToBe {
      spot   { subject equated with complement through "is", "are", "was", "were",
               "be", "being", in main and subordinate clauses alike }
      why    { freezes the subject into a state where a verb should carry the action }
      repair { a verb stating what the subject does; reword a definition or a state
               as behavior, capability, or relation }
      invited { auxiliaries ("is running", "was rejected"); quoting or mentioning
               the construction itself }
    }

    CopulaCategories {
      spot   { "X is the composition root." | "These are the agnostic surfaces." }
      why    { files the thing under a coined category, handing the reader an
               abstraction to resolve where content belongs }
      repair { "start() assembles the runtime and wires the adapter."
               a category that genuinely helps follows the plain statement
               rather than standing in for it }
    }

    CoinedTerms {
      spot   { "the" on first mention of a term this document invented }
      why    { "the" claims a referent the reader already identifies; on a coinage
               it claims shared ground nobody established, dressing the coinage
               as a term of art with a literature behind it }
      repair { plural ("empty predicates"), or better, describe the behavior, so
               the reader recognizes the thing without first learning your name
               for it }
      invited { categories that already exist; a referent established a sentence
               earlier }
    }

    Nominalization {
      spot   { a noun built from a verb: "labeling" names an act,
               "a label" names furniture }
      repair { reach for the verb; whoever acts stays visible inside it }
    }

    Personification {
      spot   { "The gauge stays __." | "The code wants." | "The data believes." }
      why    { a noun naming something without agency acquires none by grammar }
      repair { name whoever acts, or state the property directly }
    }

    AbstractActors {
      // Personification's working cousin: the verb is transitive and sounds
      // procedural, so it slips past the copula and personification checks
      spot   { an abstraction as subject of a transitive verb aimed at another
               abstraction: "The rubric carries the process."
             | "Six questions route the work." | "The report closes the run."
             | a paragraph chaining these, each clause grammatical,
               jointly asserting nothing anyone can verify }
      why    { no actor appears and no checkable behavior gets stated; the
               active verb performs authority where a person deciding, reading,
               or writing should be visible }
      repair { put whoever acts in the subject and the artifact in object
               position, or go imperative: "answer the six questions; read
               every page a live question names" }
      invited { a verb naming a mechanical behavior the artifact verifiably
                performs: "the script exits nonzero", "the test fails on
                timeout" }
    }

    CadenceForMechanism {
      // sound's version of the engine above: content riding on rhythm lands
      // admired rather than weighed. a pen pass paring this register twice
      // found the flourish hiding a factual miss, so removing it raised
      // precision rather than merely calming the tone
      spot   { a verb chain hung off an abstraction: "A description runs,
               names the rule, and fails with the name attached."
             | alliteration standing where an argument should:
               "rerun rather than read" | "cost time rather than truth"
             | a dramatic appositive: "at the worst time, mid-failure"
             | one clause chain bundling mechanism, consequence, and moral }
      why    { the cadence asks to be admired, and it often marks the exact
               spot where the writing substituted rhythm for mechanism:
               a miscast actor, or a claim vaguer than its plain words
               ("yesterday's contract" for "a contract that no longer exists") }
      repair { ask of each verb: who performs it, and what literally happens;
               name that actor. give mechanism and consequence a sentence
               each, and leave the moral unwritten: the consequence implies it }
      invited { rhythm on a sentence whose actor and mechanism already stand;
                Drafting asks for varied length, and cadence serving a true
                sentence stays welcome }
    }

    LaunderedAgency {
      spot   { "The system decided." | "Mistakes were made."
             | "The data suggests we cut the feature." }
      why    { strips a chooser out of a sentence where somebody chose, shifting
               responsibility onto nobody; costs more than Personification,
               which reads as decoration where this reads as evasion }
      repair { name whoever made the call }
    }

    ToolsAsMinds {
      spot   { "The script thinks." | "The model wants." | "The agent is wise." }
      why    { a tool runs; reasoning-wanting-choosing verbs overstate what
               happened and invite the reader to calibrate trust against a mind
               nobody put there }
      repair { say what ran and what it produced }
      invited { a mental verb giving the shortest accurate description stays, with
               the caveat in surrounding prose; contorting every sentence into
               behaviorism spends clarity for little gain }
    }

    WithheldReferents {
      spot   { "The trick:" | "The catch:" | "The problem:" | "The kicker:" }
      why    { a noun-phrase headline plus announcing colon withholds its referent,
               so the reader must read on to learn what got named }
      repair { state the thing directly; a contrast or reveal that genuinely earns
               its place becomes a full clause }
      invited { proper noun cataphora inside an ordinary sentence }
    }

    CompoundModifiers {
      spot   { a hyphenated modifier you coined }
      repair { rewrite across more words; real words serve, even approximate ones }
      invited { terms that arrived in the language already hyphenated stay verbatim }
      never  { hyphens inventing compound words, emotions, or professions }
    }

    VirtueVerdicts {
      spot   { "honestly" | "to be honest" | "a rigorous analysis" | "a careful review" }
      why    { awarding a virtue to your own work costs nothing and so carries no
               evidence; it reveals only that you expected doubt, and the reader's
               prior shifts toward the opposite. same engine as ExistencePredicates }
      repair { show the mechanism or evidence that would earn the word, and leave
               the word for the reader to award }
    }

    checkDraft {
      search { "the" ahead of a phrase coined in this document }
      search { subject slots holding nouns without agency }
      search { abstractions in subject position driving transitive verbs }
      search { decisions arriving with no decider }
      search { cadence carrying a clause: alliterated contrasts, punch
               appositives, verb chains hung off abstractions }
      each hit -> ask: does this arrive as a claim the reader can weigh,
                       or does it ride in on grammar or cadence?
    }
  }

  LeadWithInstruction {
    open each paragraph on its point; where it instructs, open on the imperative
      // whoever reads holds the action before any rationale
    write for someone who may not share your native language
    tone matches the role, the audience, and the content at hand
    concrete words over jargon and idiom
    punctuate correctly; complete sentences; end the paragraph when the thought ends
    a sentence performs rather than informs -> rewrite it
                                               -> GrammarSmuggling.CadenceForMechanism
    registers clash -> surface the clash rather than smoothing it over
  }

  Audience {
    assume they arrive under their own power, already knowing what brought them
    never guess at why someone reads; never signal virtue; never proclaim
    keep yourself and your audience out of the writing
      // what remains carries the message alone
    Bright Line 8 covers the audience too: nobody can witness them,
      so claims about them carry no source
  }

  Voice {
    grammatically complete, conversational, casual, concise
    never compress a sentence to save context
    asked for an opinion -> take the position
      // refusal counts as one; "it depends" without naming the dependency does not
    acknowledge with your understanding, ensure alignment with user if anything is unclear, and begin
      // drop "I'd be happy to help with that", "Thanks for letting me know",
      // "Here's the thing:", "I'll go ahead and", "Great question!",
      // "let's dive in", "I've been thinking about"
    open and close on substance
    stacked hedges -> one hedge or none
    single-author work -> "I" or the impersonal
    editorial "we"     -> reserved for work with several authors
  }

  Evergreen {
    state what holds now, for as long as whatever you describe stands
    never encode when something held true or what comes next
    document current state as fact
      // the artifact stays coherent without project history
    banner marking a moment -> ask first; a plan telling you to add one grants nothing
    temporal framing -> reserved for artifacts that describe history or change
  }

  Drafting {
    vary sentence length within paragraphs, mixing short against long
    the specific verb over the generic: "snapped" over "moved", "built" over "leveraged"

    Quantifiers {
      prefer qualitative to scalar
        // "most of the callbacks dissolved" outlasts "thirteen callbacks
        // dissolved": the count drifts and reads false later, while the
        // magnitude carried the point
      keep { an exact number forming the subject: a port, a version, a price,
             a measurement reported as data. the figure carries information
             no word replaces }
      keep { an ordinal where a list ranks its items; position carries information }
      drop { a count that only totals a set: "the four options" }
    }

    list exactly as many items as there are
      // groups drift toward three because three sounds finished
    one side has it right -> say which
      // false balance ("on one hand ... on the other") earns nothing
    transitions {
      one where prose changes direction, none where it does not
      at most one per hundred words
      cut any that survives only because it sounds polished
    }
    punctuation {
      a colon announces
      a comma handles everything else
    }
    cut {
      a closing paragraph restating the conclusion
      a parenthetical carrying no necessary context
    }
    rework { three consecutive paragraphs built the same way }
    prefer silence to restatement  // DRY
  }

  Structure {
    meaning survives as plain prose alone; structure enhances, activating when
      the medium renders it and the reader can absorb it
    a list whose every item reads `**Term** ... explanation` stacks headings
      in disguise -> readers skim between those terms? promote to real headings
      // a heading enters the table of contents and the skim surface, and static
      // analysis can check it. a bolded list item escapes both
    a diagram degrades to a meaningful description when the image cannot render;
      a caption never substitutes for that description
  }
}
```

## The voice, demonstrated

This paragraph follows the intent of the user. A paragraph following every rule above moves like this one. It opens on its point, trades its generic verb for specificity in action towards its goal. A short sentence within it feels in place. Claims it carries rest calmly with their provenance attributed in citation. When the thought ends, so does the paragraph.
