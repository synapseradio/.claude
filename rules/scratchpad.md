# Scratchpad

```sudolang
Scratchpad {
  // the harness environment section names a session scratchpad directory
  // and asks that all temporary files go there instead of /tmp. that
  // instruction stands. this rule only redirects where it points.

  Redirect {
    inside a git repository  -> every path the harness gives as the scratchpad
                                directory resolves to `scratchpad/` at that
                                repository's root
      // read the harness instruction as naming that directory, and write there
    outside a git repository -> the harness path stands exactly as given
    skills and workflows naming their own default (a run file at
      `/tmp/<skill>-<slug>.md`) redirect the same way:
      `scratchpad/<skill>-<slug>.md`; say once where the file went
  }

  SettingUp {
    first write in a repository -> in the same action {
      create `scratchpad/`
      add `scratchpad/` to that repository's `.gitignore`,
        under a comment naming what lives there
    }
    // both steps land before the first file, so nothing untracked
    // is ever left staged for a commit
    plan mode holds  -> working notes go into the plan file;
                        `scratchpad/` arrives on the first write once
                        writing opens up
    a read-only mode -> suspends both setup steps  // neither can run there
  }

  WhyTheRedirect {
    a session directory disappears with the session and sits far from
      the code its notes describe
    a repository-local directory {
      keeps working notes beside the thing they are about
      survives across sessions
      stays reachable by ordinary tools
        // the user opens it in their editor, greps it, reads a review
        // from three weeks ago without knowing a session id
    }
    gitignoring it keeps that convenience out of history
  }

  Covers {
    everything the harness instruction already covers: intermediate results,
      working files, throwaway scripts, generated data, any output that does
      not belong in the user's project
    reviews, audits, plans, and run files land here too
  }

  NeverCovers {
    deliverables {
      documentation the project ships   -> its docs tree
      source                            -> its source tree
      a file the user asked for by name -> where they named it
    }
    secrets and credentials belong in neither place
    never write into `scratchpad/` to avoid deciding where a real artifact lives
    cannot tell whether output is a deliverable -> ask
  }
}
```
