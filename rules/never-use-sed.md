# Never Use sed for Edits

```sudolang
NeverUseSedForEdits {
  Applies { always }

  StreamEditors = [sed, gsed, awk, etc]

  Constraints {
    never use StreamEditors to modify a file
    always use Edit or Write instead
      // they match exactly, fail loudly on a wrong match,
      // and never silently mangle the rest of the file
    triviality is no exemption {
      one-line substitution -> Edit
      in-place delete       -> Edit
      appending a line      -> Edit|Write
    }
  }

  Allowed {
    StreamEditors for read-only inspection in a pipeline
      // touches no file on disk; the ban covers writing only
    Perl the user has explicitly approved for the edit at hand
      // approval names this edit, and does not carry to the next one
  }
}
```
