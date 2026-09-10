# Settings reference

What a valid settings change looks like, key by key. Which file a change
lands in belongs to SKILL.md.

## Contents

- [Permissions](#permissions)
- [Environment variables](#environment-variables)
- [Model and agent](#model-and-agent)
- [Attribution on commits and PRs](#attribution-on-commits-and-prs)
- [MCP server management](#mcp-server-management)
- [Plugins](#plugins)
- [Sandbox](#sandbox)
- [Other settings](#other-settings)
- [Example workflows](#example-workflows)
- [Mistakes that cost the most](#mistakes-that-cost-the-most)
- [The full settings schema](#the-full-settings-schema)

## Permissions

```json
{
  "permissions": {
    "allow": ["Bash(npm *)", "Edit(.claude)", "Read"],
    "deny": ["Bash(rm -rf *)"],
    "ask": ["Edit(/etc/*)"],
    "defaultMode": "default",
    "additionalDirectories": ["/extra/dir"]
  }
}
```

`defaultMode` takes `"default"`, `"plan"`, `"acceptEdits"`, or `"dontAsk"`.

Permission rule syntax:

| Form | Example | Matches |
|------|---------|---------|
| Exact match | `"Bash(npm run test)"` | that command alone |
| Prefix wildcard | `"Bash(git *)"` | `git`, `git status`, `git commit`, and the rest |
| Colon prefix | `"Bash(npm view:*)"` | `npm view` and anything following it |
| Tool only | `"Read"` | every call of that tool |
| MCP tool | `"mcp__tavily__tavily_search"` | that MCP tool |

`deny` beats `ask`, and `ask` beats `allow`.

## Environment variables

```json
{
  "env": {
    "DEBUG": "true",
    "MY_API_KEY": "value"
  }
}
```

Every value is a string, including numbers and flags.

## Model and agent

```json
{
  "model": "sonnet",
  "agent": "agent-name",
  "alwaysThinkingEnabled": true
}
```

`model` takes `"fable"`, `"opus"`, `"sonnet"`, `"haiku"`, or a full model ID.

## Attribution on commits and PRs

```json
{
  "attribution": {
    "commit": "Custom commit trailer text",
    "pr": "Custom PR description text"
  }
}
```

Setting `commit` or `pr` to the empty string `""` hides that attribution.

## MCP server management

```json
{
  "enableAllProjectMcpServers": true,
  "enabledMcpjsonServers": ["server1", "server2"],
  "disabledMcpjsonServers": ["blocked-server"]
}
```

## Plugins

```json
{
  "enabledPlugins": {
    "formatter@anthropic-tools": true
  }
}
```

Plugin syntax is `plugin-name@source`, where source is
`claude-code-marketplace`, `claude-plugins-official`, or `builtin`.

## Sandbox

```json
{
  "sandbox": {
    "enabled": false,
    "autoAllowBashIfSandboxed": true,
    "allowUnsandboxedCommands": false,
    "enableWeakerNetworkIsolation": true,
    "excludedCommands": ["docker"],
    "network": {
      "allowedDomains": ["github.com", "*.npmjs.org"],
      "allowLocalBinding": true
    },
    "filesystem": {
      "allowWrite": ["/tmp", "~/.cache"],
      "allowRead": ["~/.ssh/known_hosts"],
      "denyRead": ["~/.aws", "*secrets*"]
    }
  }
}
```

Filesystem entries take a leading `/` for an absolute path and a leading `~/`
for a path under the home directory. A doubled slash such as `//tmp` names a
path the sandbox does not resolve as intended, and the alignment sweep
corrects it toward the spelling `settings.base.json` carries.

## Other settings

| Key | Effect |
|-----|--------|
| `language` | Preferred response language, such as `"japanese"` |
| `cleanupPeriodDays` | Days to keep transcripts before automatic cleanup, default 30, minimum 1 |
| `respectGitignore` | Whether to respect `.gitignore`, default `true` |
| `spinnerTipsEnabled` | Show tips in the spinner |
| `timeFormat` | Clock format in the UI: `"auto"`, `"12-hour"`, `"24-hour"`, `"24-hour-utc"`, or a strftime pattern such as `"%H:%M"` |
| `timeZone` | IANA time zone for times in the UI, such as `"UTC"`, default the system zone |
| `spinnerVerbs` | Customize spinner verbs, `{ "mode": "append" or "replace", "verbs": [...] }` |
| `spinnerTipsOverride` | Override spinner tips, `{ "excludeDefault": true, "tips": ["Custom tip"] }` |
| `syntaxHighlightingDisabled` | Disable diff highlighting |

## Example workflows

### Adding a hook

The user asks to format code after Claude writes it.

1. Clarify which formatter, whether prettier, gofmt, or another.
2. Read the target file.
3. Merge into the existing hooks rather than replacing them.
4. Result:

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

### Adding a permission

The user asks to allow npm commands without prompting.

1. Read the existing permissions.
2. Add `Bash(npm *)` to the `allow` array, keeping every entry already there.
3. Report the combined result.

### Setting an environment variable

The user asks to set `DEBUG=true`.

1. Decide the scope, whether user settings or project settings.
2. Read the target file.
3. Merge into the `env` object:

```json
{ "env": { "DEBUG": "true" } }
```

## Mistakes that cost the most

1. **Replacing instead of merging.** Writing an array wholesale drops every
   entry already in it.
2. **The wrong file.** Ask when the scope is unclear.
3. **Invalid JSON.** A malformed settings file silently disables every
   setting in it. Validate with `jq -e . FILE` after every change.
4. **Writing before reading.** Read the target file first, every time.

## The full settings schema

`settings-schema.json` in this directory holds the published JSON schema for
Claude Code settings, and `schema-cache.md` records the version it was
fetched against and how to refresh it. Consult the schema to confirm a key
name, its type, and its allowed values before writing a key you have not
written before.

Read one property out of it rather than the whole file:

```bash
jq '.properties.KEYNAME' ${CLAUDE_PLUGIN_ROOT}/skills/update-claude-settings/references/settings-schema.json
```

List every property name it defines:

```bash
jq -r '.properties | keys[]' ${CLAUDE_PLUGIN_ROOT}/skills/update-claude-settings/references/settings-schema.json
```
