# Hooks reference

Hooks run commands at points in Claude Code's lifecycle. The harness executes
a hook, so a hook is the only way to make something happen automatically in
response to an event. A memory entry or a stated preference cannot do it.

## Contents

- [When a request needs a hook](#when-a-request-needs-a-hook)
- [Hook structure](#hook-structure)
- [Hook events](#hook-events)
- [Hook types](#hook-types)
- [Hook input on stdin](#hook-input-on-stdin)
- [Hook JSON output](#hook-json-output)
- [Common patterns](#common-patterns)
- [Constructing a hook with verification](#constructing-a-hook-with-verification)
- [Troubleshooting a hook that does not run](#troubleshooting-a-hook-that-does-not-run)

## When a request needs a hook

A request that names an event and an automatic response to it needs a hook:

- "Before compacting, ask me what to preserve" needs a PreCompact hook.
- "After writing files, run prettier" needs a PostToolUse hook with a
  `Write|Edit` matcher.
- "When I run bash commands, log them" needs a PreToolUse hook with a `Bash`
  matcher.
- "Always run tests after code changes" needs a PostToolUse hook.

## Hook structure

```json
{
  "hooks": {
    "EVENT_NAME": [
      {
        "matcher": "ToolName|OtherTool",
        "hooks": [
          {
            "type": "command",
            "command": "your-command-here",
            "timeout": 60,
            "statusMessage": "Running..."
          }
        ]
      }
    ]
  }
}
```

## Hook events

| Event | Matcher | Purpose |
|-------|---------|---------|
| PermissionRequest | Tool name | Runs before the permission prompt |
| PreToolUse | Tool name | Runs before the tool, can block |
| PostToolUse | Tool name | Runs after a successful tool call |
| PostToolUseFailure | Tool name | Runs after a tool call fails |
| Notification | Notification type | Runs on notifications |
| Stop | none | Runs when Claude stops, including clear, resume, and compact |
| PreCompact | "manual" or "auto" | Runs before compaction |
| PostCompact | "manual" or "auto" | Runs after compaction, receives the summary |
| UserPromptSubmit | none | Runs when the user submits |
| SessionStart | none | Runs when a session starts |

Common tool matchers: `Bash`, `Write`, `Edit`, `Read`, `Glob`, `Grep`.

## Hook types

A command hook runs a shell command:

```json
{ "type": "command", "command": "prettier --write $FILE", "timeout": 30 }
```

A prompt hook evaluates a condition with the model:

```json
{ "type": "prompt", "prompt": "Is this safe? $ARGUMENTS" }
```

An agent hook runs an agent with tools:

```json
{ "type": "agent", "prompt": "Verify tests pass: $ARGUMENTS" }
```

Prompt hooks and agent hooks attach to the tool events alone: PreToolUse,
PostToolUse, PermissionRequest.

## Hook input on stdin

The harness pipes one JSON object to the hook on stdin:

```json
{
  "session_id": "abc123",
  "tool_name": "Write",
  "tool_input": { "file_path": "/path/to/file.txt", "content": "..." },
  "tool_response": { "success": true }
}
```

`tool_response` appears on PostToolUse alone.

## Hook JSON output

A hook returns JSON on stdout to control what happens next:

```json
{
  "systemMessage": "Warning shown to user in UI",
  "continue": false,
  "stopReason": "Message shown when blocking",
  "suppressOutput": false,
  "decision": "block",
  "reason": "Explanation for decision",
  "hookSpecificOutput": {
    "hookEventName": "PostToolUse",
    "additionalContext": "Context injected back to model"
  }
}
```

| Field | Effect |
|-------|--------|
| `systemMessage` | Displays a message to the user, on every hook |
| `continue` | `false` blocks or stops, default `true` |
| `stopReason` | The message shown when `continue` is `false` |
| `suppressOutput` | Hides stdout from the transcript, default `false` |
| `decision` | `"block"` for PostToolUse, Stop, and UserPromptSubmit hooks. PreToolUse deprecates this field in favor of `hookSpecificOutput.permissionDecision` |
| `reason` | The explanation for `decision` |
| `hookSpecificOutput` | Event-specific output, and it carries `hookEventName` |

Inside `hookSpecificOutput`:

| Field | Effect |
|-------|--------|
| `additionalContext` | Text injected into the model's context |
| `permissionDecision` | `"allow"`, `"deny"`, or `"ask"`, PreToolUse alone |
| `permissionDecisionReason` | The reason for that decision, PreToolUse alone |
| `updatedInput` | Modified tool input, PreToolUse alone |

## Common patterns

Auto-format after writes:

```json
{
  "hooks": {
    "PostToolUse": [{
      "matcher": "Write|Edit",
      "hooks": [{
        "type": "command",
        "command": "jq -r '.tool_response.filePath // .tool_input.file_path' | { read -r f; prettier --write \"$f\"; } 2>/dev/null || true"
      }]
    }]
  }
}
```

Log all bash commands:

```json
{
  "hooks": {
    "PreToolUse": [{
      "matcher": "Bash",
      "hooks": [{
        "type": "command",
        "command": "jq -r '.tool_input.command' >> ~/.claude/bash-log.txt"
      }]
    }]
  }
}
```

A Stop hook that displays a message to the user. The command writes JSON
carrying a `systemMessage` field:

```bash
echo '{"systemMessage": "Session complete!"}'
```

Run tests after code changes:

```json
{
  "hooks": {
    "PostToolUse": [{
      "matcher": "Write|Edit",
      "hooks": [{
        "type": "command",
        "command": "jq -r '.tool_input.file_path // .tool_response.filePath' | grep -E '\\.(ts|js)$' && npm test || true"
      }]
    }]
  }
}
```

## Constructing a hook with verification

Given an event, a matcher, a target file, and a desired behavior, follow this
flow. Each step catches a different failure class, and a hook that silently
does nothing costs more than no hook at all.

1. **Dedup check.** Read the target file. Where a hook already sits on the
   same event and matcher, show the existing command and ask whether to keep
   it, replace it, or add alongside.

2. **Construct the command for this project.** The hook receives JSON on
   stdin. Build a command that:
   - Extracts the payload safely, through `jq -r` into a quoted variable or
     `{ read -r f; ... "$f"; }`, never through unquoted `| xargs`, which
     splits on spaces.
   - Invokes the underlying tool the way this project runs it. Check for
     npx, bunx, yarn, pnpm, a Makefile target, or a global install.
   - Skips inputs the tool does not handle. Formatters often carry
     `--ignore-unknown`; where one does not, guard by extension.
   - Stays raw at this stage, with no `|| true` and no stderr suppression.
     The wrapping comes after the pipe test passes.

3. **Pipe-test the raw command.** Synthesize the stdin payload the hook will
   receive and pipe it in directly:
   - PreToolUse or PostToolUse on `Write|Edit`:
     `echo '{"tool_name":"Edit","tool_input":{"file_path":"REAL_FILE"}}' | CMD`
   - PreToolUse or PostToolUse on `Bash`:
     `echo '{"tool_name":"Bash","tool_input":{"command":"ls"}}' | CMD`
   - Stop, UserPromptSubmit, SessionStart: most commands read no stdin, so
     `echo '{}' | CMD` suffices.

   Check the exit code and the side effect, that the file really got
   formatted or the test really ran. A failure here returns a real error:
   fix it, whether the package manager is wrong, the tool is missing, or the
   jq path is wrong, and retest. Once it works, wrap it with
   `2>/dev/null || true`, unless the user wants a blocking check.

4. **Write the JSON.** Merge into the target file using the shape under
   [Hook structure](#hook-structure). Where this creates
   `.claude/settings.local.json` for the first time, add it to `.gitignore`,
   since the Write tool adds no gitignore entry.

5. **Validate syntax and shape in one shot:**

   ```bash
   jq -e '.hooks.EVENT[] | select(.matcher == "MATCHER") | .hooks[] | select(.type == "command") | .command' TARGET_FILE
   ```

   Exit 0 with your command printed means the shape is correct. Exit 4 means
   the matcher does not match. Exit 5 means malformed JSON or wrong nesting.
   A broken settings file silently disables every setting in that file, so
   repair any pre-existing malformation too.

6. **Prove the hook fires.** This step applies to PreToolUse and PostToolUse
   on a matcher you can trigger in-turn, `Write|Edit` through Edit and `Bash`
   through Bash. Stop, UserPromptSubmit, and SessionStart fire outside the
   turn, so skip to step 7 for those.

   For a formatter on PostToolUse with `Write|Edit`, introduce a detectable
   violation through Edit, such as two consecutive blank lines, bad
   indentation, or a missing semicolon, something this formatter corrects.
   Trailing whitespace does not work, since Edit strips it before writing.
   Re-read the file and confirm the hook fixed it.

   For anything else, temporarily prefix the command in the settings file
   with `echo "$(date) hook fired" >> /tmp/claude-hook-check.txt; `, trigger
   the matching tool, and read the sentinel file.

   Clean up either way: revert the violation and strip the sentinel prefix,
   whether the proof passed or failed.

   Where the proof fails while the pipe test and the `jq -e` check both
   passed, the settings watcher is not watching that directory. It watches
   only directories that held a settings file when the session started. The
   hook is written correctly. Tell the user to open `/hooks` once, which
   reloads the config, or to restart. You cannot do this yourself, since
   `/hooks` is a user menu and opening it ends the turn.

7. **Handoff.** Tell the user the hook is live, or that it needs `/hooks` or
   a restart under the watcher caveat. Point them at `/hooks` to review,
   edit, or disable it. The UI shows "Ran N hooks" only when a hook errors or
   runs slowly, so silent success is invisible by design.

## Troubleshooting a hook that does not run

1. **Read the settings file.** Check `~/.claude/settings.json` or
   `.claude/settings.json`, whichever scope holds the hook.
2. **Check the JSON syntax.** Invalid JSON fails silently.
3. **Check the matcher.** Confirm it matches the tool name, such as `Bash`,
   `Write`, or `Edit`.
4. **Check the hook type.** Confirm it is `command`, `prompt`, or `agent`.
5. **Run the command manually** with a synthesized stdin payload.
6. **Run `claude --debug`** to see hook execution logs.
