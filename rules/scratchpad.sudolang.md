# Scratchpad

Every temporary or working file lands in `scratchpad/` at the root of the
repository in play. The harness environment section names a session scratchpad
directory and asks that all temporary files go there instead of /tmp. That
instruction stands, and only its destination changes.

Scratchpad {
  Applies { any temporary or working file }

  Redirect {
    match (where the work runs) {
      case (inside a git repository) =>
        read every path the harness gives as the scratchpad directory as
        naming `scratchpad/` at that repository's root, and write there
      case (outside a git repository) =>
        the harness path stands exactly as given
    }
    (a skill or workflow names its own default, a run file at
      `/tmp/<skill>-<slug>.md`) =>
      redirect it the same way to `scratchpad/<skill>-<slug>.md`, and say
      once where the file went
  }

  SettingUp {
    fn firstWrite(repository) {
      create `scratchpad/`, and stop there: the global gitignore at
        `~/.dotfiles/git/ignore` already covers `scratchpad/` on this
        machine, so nothing goes in the repository's own gitignore
    }
    Constraints {
      while plan mode holds, working notes go into the plan file, and
        `scratchpad/` arrives on the first write once writing opens up
      skip setup while a read-only mode holds, since that mode permits no
        write
    }
  }

  WhyTheRedirect {
    a session directory disappears with the session and sits far from
      the code its notes describe
    a repository-local directory {
      keeps working notes beside the thing they are about
      survives across sessions
      stays reachable by ordinary tools
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
      (documentation the project ships)   => its docs tree
      (source)                            => its source tree
      (a file the user asked for by name) => where they named it
    }
    (a fact worth keeping across sessions) => PersistentMemory picks its store
    Constraints {
      secrets and credentials belong in neither place
    }
    require you never write into `scratchpad/` to avoid deciding where a
      real artifact lives
    (you cannot tell whether output is a deliverable) => ask
  }
}
