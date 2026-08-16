Scratchpad {
  Applies { any temporary or working file: intermediate results, throwaway
            scripts, generated data, reviews, audits, plans, run files }

  Layout {
    root = "scratchpad/" at the root of the repository in play
    dir = if (`git branch --show-current` names a branch) "$root/$branch/"
      else root
    file = "$dir/$YYYYMMDD-HHmm-$slug.md", timestamped at the first write
  }

  constraint RedirectTheHarnessPath {
    (inside a git repository) => read every path the harness gives as its
      scratchpad or temp directory as naming Layout.dir, and write there
    (outside a git repository) => use the harness path exactly as given
    (a skill or workflow names a default such as `/tmp/<skill>-<slug>.md`)
      => write it at Layout.file with that slug, and say once where it went
  }

  constraint SetupStopsAtMkdir {
    create Layout.dir on first write and change nothing else: the global
      gitignore at `~/.dotfiles/git/ignore` already covers `scratchpad/`
    (plan mode holds) => keep working notes in the plan file until writing
      opens up
    (a read-only mode holds) => skip setup
  }

  constraint NeverForDeliverables {
    require documentation the project ships goes to its docs tree, source to
      its source tree, and a file the user named to where they named it
    require no secret or credential lands in `scratchpad/`
    require you never write into `scratchpad/` to avoid deciding where a
      real artifact lives
    (a fact is worth keeping across sessions) => store it under
      PersistentMemory
    (you cannot tell whether output is a deliverable) => ask
  }
}
