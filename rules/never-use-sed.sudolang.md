NeverUseSedForEdits {
  Applies { always }

  StreamEditors = [sed, gsed, awk, `perl -i`, and any tool substituting in
    place from a pattern it never shows you]

  constraint EditsShowTheirMatch {
    require no StreamEditor ever modifies a file, whatever the hook catches
    use Edit or Write for every change, a one-line substitution and an
      appended line included, since each matches exactly and fails on a
      wrong match rather than mangling the rest of the file
    use a StreamEditor only for read-only inspection in a pipeline that
      touches no file on disk
  }

  constraint ScriptedEdit {
    Applies { a change repeating mechanically across many files or lines }
    write the script in a real language: Python, TypeScript, JavaScript,
      Ruby, or the like, matching exact strings rather than loose patterns
    require a checkpoint before it runs, `git commit` or `git stash`, so the
      script's whole effect stands as the only uncommitted diff
    (no checkpoint) => do not run the script
    checkpoint |> run |> report what changed |> read the diff
      |> run again and confirm it reports no change
  }
}
