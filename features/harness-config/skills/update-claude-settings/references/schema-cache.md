# The cached settings schema

`settings-schema.json` in this directory is a byte-exact copy of the
published Claude Code settings schema.

| Field | Value |
|-------|-------|
| Source URL | `https://json.schemastore.org/claude-code-settings.json` |
| `$id` | `https://json.schemastore.org/claude-code-settings.json` |
| Schema dialect | `http://json-schema.org/draft-07/schema#` |
| Claude Code version it was fetched against | 2.1.261 |
| Size | 230217 bytes |
| SHA-256 | `6d4a6e3c7adedffce8079ccaef0a4bab5f5718b054421b4475c788a0ae4bedfe` |
| Top-level properties | 142 |
| `additionalProperties` | `true` |

`additionalProperties: true` is what lets `settings.base.json` carry the
`alignment` registry without failing schema validation.

## Refreshing it

```bash
curl -sfL https://json.schemastore.org/claude-code-settings.json \
  -o ${CLAUDE_PLUGIN_ROOT}/skills/update-claude-settings/references/settings-schema.json
```

Use curl. It returns byte-exact JSON. The tavily and linkup tools return
markdown optimized for a model to read, which corrupts a schema file, and
`settings.base.json` denies the `WebFetch` and `WebSearch` tools.
`Bash(curl:*)` sits in no deny or ask list, and only `curl * | sh` sits in
`ask`, so a plain curl runs without a prompt.

After refreshing, update the version, size, SHA-256, and property count in
the table above:

```bash
F=${CLAUDE_PLUGIN_ROOT}/skills/update-claude-settings/references/settings-schema.json
wc -c < "$F"; shasum -a 256 "$F"; jq '.properties | length' "$F"
```

## When to refresh

Refresh when a key the user names is missing from the cached copy, or when
`jq '.properties | has("KEYNAME")'` returns `false` for a key the running
CLI accepts. The cache goes stale only toward new keys, and a missing key is
the signal that triggers the refresh.
