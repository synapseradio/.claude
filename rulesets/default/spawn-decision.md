<!-- rule: spawn-decision -->

## spawn-decision

For every step of work a delegate could take, optimize for a step done by the cheapest tier able to take it, with your own context kept for the conversation.

Hold every spawn as costing about 50k tokens of fresh context before its first act, about half a cent on haiku, a dime on sonnet, twenty cents on opus, and fifty cents on fable, with the user waiting on it. Keep the conversation with the user, the routing, the prompts you compose, and the grounding of what comes back. Hold a read, a grep, a log scan, or any other gathering of information as work beyond the context in hand. Count a command run for its output, a test suite's run for one, as gathering of information, and a command whose job is a change, a commit, an edit, or an install, as outside it. Take the first arm that fits.

route step
  | a step finishes in one tool call with the context in hand = act directly
  | a fix for a break would pull you off the current task = spawn it
  | a step is the Read of a file that the Edit tool, or the Write tool over an existing file, requires before your next change to that file, the reading of the newest handoff note at a session's first turn, the opening of a cited line to confirm it backs a claim, or a scan of a saved command output by grep, jq, ast-grep, or a Read by line range
      = act directly
  | a step is any other read, scan, or gathering of information, and you hold no tool that spawns an agent
      = act directly
  | a step is any other read, scan, or gathering of information
      = spawn it to a fresh haiku, one haiku holding the step's related reads > parallel haikus, each command run's output saved by the haiku to a file in the scratchpad
  | a step is a read, a map, an implementation, a critique, a design, or a plan
      = spawn it to the cheapest tier able to take it
