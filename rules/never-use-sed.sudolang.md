# Never Use sed for Edits

Every edit goes through a tool that shows what it matched: Edit, Write, or a
script in a real language that reports what it changed. Stream editors driving
in-place substitution stay out of any path that writes a file.

NeverUseSedForEdits {
  Applies { always }

  StreamEditors = [sed, gsed, awk, `perl -i`, and any tool substituting in
    place from a pattern it never shows you]

  require StreamEditors never modify a file, and hold `perl -i` and every
    other editor on that list to that ban yourself, since
    ../scripts/hooks/deny-inplace-stream-edit.sh, a PreToolUse hook on Bash,
    denies `sed -i`, `gsed -i`, and `awk -i inplace` alone

  Constraints {
    prefer Edit or Write wherever either expresses the change, since each
      matches exactly and fails loudly on a wrong match rather than mangling
      the rest of the file
    triviality exempts nothing, so match (the change) {
      case (a one-line substitution) => Edit
      case (an in-place delete)      => Edit
      case (appending a line)        => Edit | Write
    }
  }

  Allowed {
    StreamEditors for read-only inspection in a pipeline that touches no file
      on disk

    a script in a real language, Python, TypeScript, JavaScript, Ruby, or the
      like, under ScriptedEdit, and reach for one wherever the change repeats
      mechanically across many files or many lines and Edit would spend a call
      per instance
  }

  ScriptedEdit {
    Applies { a script modifying more than a single line of code }

    require a checkpoint first: `git commit` or `git stash`, leaving the
      script's whole effect as the only uncommitted diff, so `git checkout`
      returns the tree
    (no checkpoint) => do not run the script

    fn run(script) {
      checkpoint |> run |> report what changed |> read the diff
        |> run again and confirm it reports no change
    }

    Constraints {
      match exact strings rather than loose patterns
    }
  }
}
