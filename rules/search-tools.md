SearchTools {
  AppliesWhen { the user says "look it up", "look this up", "verify this",
            "check this", or anything equivalent
            | about to write a call, flag, or config key against a package
              the lockfile resolves
            | a tool call just failed }

  constraint TheLiveWebAnswers {
    search the live web, and let no local source, package file, or
      installed library code stand in for it, since a copy on disk records
      what someone installed once
    omit years from search queries unless the user supplies one
    cite each source you rely on by URL
  }

  constraint SearchToolBan {
    (a live-web search is due) => search through the first of these this
      session exposes: crwl, tvly, linkup
    (the chosen tool errors or returns nothing usable) => fall to the next
      one, and name which tool answered
  }

  constraint ReadBeforeTheFirstCall {
    AppliesWhen { about to write a call, flag, or config key against a package
              the lockfile resolves }
    read the current documentation for the resolved version before writing
      the first line against it, and let no recollection of the interface
      stand in for that read
    (the resolved version postdates what you recall of the package) => treat
      every signature you remember as a guess until the read confirms it
  }

  constraint AFailureBuysALookup {
    AppliesWhen { a tool call just failed }
    stop, and read the error before choosing what to do next
    require you never attempt again from the recollection that produced the
      failure, since a failure against an interface reports a wrong model of
      that interface rather than a wrong keystroke
    next = match (the error) {
      case (it names its own fix: a linter rule carrying its replacement, a
            compiler suggestion, a usage line) => apply what it names, and
            skip lookup()
      case (it is the red step you predicted before writing the code) => say
            so in one clause and carry on to the code that makes it pass
      default => run lookup(), and resume from what it returns
    }
    (a second failure follows with no success between) => search the error
      text verbatim before anything else
  }

  constraint BothSourcesAtOnce {
    AppliesWhen { lookup() runs }
    issue the installed-artifact read and the live-web search in one
      response, and let neither wait on the other
    read the installed artifact for what the resolved version does: its
      types, its `--help` output, its bundled documentation
    read the live web for what the package documents now, and for the
      version the docs describe
    (the two disagree) => follow the installed artifact for behavior, name
      the disagreement to the user, and give the version each source
      describes
  }

  fn lookup() {
    name the interface in question and the version the lockfile resolves
      |> read the installed artifact and search the live web together under
         via(BothSourcesAtOnce)
      |> state what the sources settled and what they left open
  }
}
