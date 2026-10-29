<!-- rule: spawn-decision -->

## spawn-decision

For every step of work a delegate could take, optimize for a step done by the cheapest tier able to take it, with your own context kept for the conversation.

Hold every spawn as costing about 50k tokens of fresh context before its first act, about half a cent on haiku, a dime on sonnet, twenty cents on opus, and fifty cents on fable, with the user waiting on it. Keep the conversation with the user, the routing, the prompts you compose, and the grounding of what comes back. Take the first arm that fits.

route step
  | a step finishes in one tool call with the context in hand = act directly
  | a fix for a break would pull you off the current task = spawn it
  | a step is a read, a map, an implementation, a critique, a design, or a plan
      = spawn it to the cheapest tier able to take it
