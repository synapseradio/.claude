## spawn-decision

For every read, scan, or other gathering of information a delegate could take, optimize for a step done by a fresh haiku, with its output kept out of your own context.

Hold a read, a grep, a log scan, or any other gathering of information as work beyond the context in hand. Count a command run for its output, a test suite's run for one, as gathering of information, and a command whose job is a change, a commit, an edit, or an install, as outside it. Take the first arm that fits.

route read
  | a step is the Read of a file that the Edit tool, or the Write tool over an existing file, requires before your next change to that file, the reading of the newest handoff note at a session's first turn, the opening of a cited line to confirm it backs a claim, or a scan of a saved command output by grep, jq, ast-grep, or a Read by line range
      = act directly
  | you hold no tool that spawns an agent = act directly
  | otherwise = spawn it to a fresh haiku, one haiku holding the step's related reads > parallel haikus, each command run's output saved by the haiku to a file in the scratchpad

State in each haiku's prompt every step, every path, the exact constraints, and the check to run and return.
Spawn a delegate only for a read, a scan, or another gathering of information.
