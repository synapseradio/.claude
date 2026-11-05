---
name: toggle
description: Change which rules the delegates this session starts from now on receive. Actions are all, none, flag NAME, unflag NAME, and clear.
disable-model-invocation: true
---

# Toggle

The command below ran with the action the person typed. Its result follows.

!`bash "${CLAUDE_PLUGIN_ROOT}/hooks/with-python.sh" "${CLAUDE_PLUGIN_ROOT}/lib/rulesets/cli.py" toggle --session "${CLAUDE_SESSION_ID}" $ARGUMENTS`

Report the result to the person in one sentence. A result that names an error is the whole report.

## Actions

Each action changes the delegates this session starts afterwards. It leaves this session's own rules and every running delegate's rules as they are.

- `all` gives each delegate every rule in the pool.
- `none` gives each delegate no rule.
- `flag NAME` gives each delegate the flag `NAME`, which the manifest declares.
- `unflag NAME` removes the flag `NAME` from each delegate, which the manifest declares.
- `clear` ends every toggle of this session, so each delegate composes from the manifest and the launch flags alone.

The later of `all` and `none` replaces the earlier. Session state ends with a clear of the session and with its close.
