<rule name="shell-quoting">

  <applies_when>
    You are making a Bash tool call.
  </applies_when>

  <optimize_for>
    a command that runs as one piece, quoted so the shell reads it whole.
    <why_it_matters>
      A command that runs whole leaves a record of what ran that can be trusted as it stands. The shell is zsh, and an unquoted `!`, `?`, or glob character breaks a multi-line command mid-run. File content pushed through echo or a heredoc can arrive altered, and Write and Edit carry it exactly.
    </why_it_matters>
  </optimize_for>

  <decide name="quote">
    Single-quote an argument that holds `!`, `?`, `*`, `[`, `]`, `$`, parentheses, or whitespace. Put multi-line or special-character content in a heredoc with a quoted delimiter, `<<'EOF'`.
  </decide>

  <require>
    Keep double quotes unnested. Carry file content into a file through Write or Edit only.
  </require>

</rule>
