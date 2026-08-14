# Never Use sed for Edits

Every edit goes through a tool that shows what it matched: Edit, Write, or a
script in a real language that reports what it changed. Stream editors driving
in-place substitution stay out of any path that writes a file.

NeverUseSedForEdits {
  Applies { always }
  // the ban covers in-place substitution over a stream, rather than writing
  // a file from a program. `sed -i` applies a pattern it never shows you to a
  // file it never reads back, so a wrong match mangles the rest silently. a
  // script reads its input, transforms it, reports what it did, and leaves a
  // way back

  StreamEditors = [sed, gsed, awk, `perl -i`, etc]
    // in-place substitution driven by a pattern, reporting nothing it matched

  require StreamEditors never modify a file
    // enforced mechanically: scripts/hooks/deny-inplace-stream-edit.sh
    // denies sed/gsed -i and awk -i inplace as a PreToolUse hook on Bash.
    // the wider ban (perl -i and kin) rests on this prose alone

  Constraints {
    prefer Edit or Write wherever either expresses the change
      // they match exactly, fail loudly on a wrong match,
      // and never silently mangle the rest of the file
    triviality exempts nothing, so match (the change) {
      case (a one-line substitution) => Edit
      case (an in-place delete)      => Edit
      case (appending a line)        => Edit | Write
    }
  }

  Allowed {
    StreamEditors for read-only inspection in a pipeline
      // touches no file on disk. the ban covers writing only

    a script in a real language, Python, TypeScript, JavaScript, Ruby, or the
      like, under ScriptedEdit
      // reach for one where the change is mechanical and repeats across many
      // files or many lines, and Edit would spend a call per instance
  }

  ScriptedEdit {
    Applies { a script modifying more than a single line of code }

    require a checkpoint first: `git commit` or `git stash`
      // the script's whole effect becomes the only uncommitted diff,
      // so `git checkout` returns the tree
    (no checkpoint) => do not run the script

    fn run(script) {
      checkpoint |> run |> report what changed |> read the diff
        |> run again and confirm it reports no change
        // idempotent: running it again changes nothing further
    }

    Constraints {
      match exact strings rather than loose patterns
    }
  }
}
