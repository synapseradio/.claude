# Claude Code environment variables — full reference

Compiled: 2026-09-08 16:08 CEST, from `https://code.claude.com/docs/en/env-vars.md` and `https://code.claude.com/docs/en/model-config.md` (Claude Code docs, version in view: 2.1.263 installed locally). "Date added" gives the version the row itself states (an explicit "Added in" or "Requires ... or later" note); a dash means the docs state no version for that variable.

## Model selection, aliases & tiers

| Variable | What it does (relation to other vars) | Use cases | Date added |
|---|---|---|---|
| `ANTHROPIC_MODEL` | Session's active model (alias or full name). Read before the `model` setting; `--model`/`/model` override it for the session | Launch on a specific model without editing settings | — |
| `ANTHROPIC_DEFAULT_MODEL` | Model new sessions start on by default, when nothing else (`--model`, `ANTHROPIC_MODEL`, any settings-file `model`, org default) selects one. Also the model `default`/Default option resolves to, unless an org default applies | Set a fleet-wide starting model without touching every settings file | v2.1.236 |
| `ANTHROPIC_DEFAULT_OPUS_MODEL` | Model ID the `opus` alias resolves to, and what `opusplan` uses during Plan Mode. Companion vars `_NAME`, `_DESCRIPTION`, `_SUPPORTED_CAPABILITIES` control its picker display/capabilities | Pin Opus to a specific version/ARN on Bedrock, Vertex, Foundry | — |
| `ANTHROPIC_DEFAULT_SONNET_MODEL` | Model ID `sonnet` resolves to, and what `opusplan` uses outside Plan Mode | Pin Sonnet version per deployment | — |
| `ANTHROPIC_DEFAULT_HAIKU_MODEL` | Model ID `haiku` resolves to; also used for background functionality. Supersedes deprecated `ANTHROPIC_SMALL_FAST_MODEL` | Pin the fast/background model | — |
| `ANTHROPIC_DEFAULT_FABLE_MODEL` | Model ID `fable` resolves to; also the ID Claude Code recognizes as a Fable model for automatic fallback on third-party providers | Pin Fable version; required for Fable-recognition-based fallback on Bedrock/Vertex/Foundry | — |
| `ANTHROPIC_DEFAULT_OPUS_MODEL_NAME` / `_SONNET_MODEL_NAME` / `_HAIKU_MODEL_NAME` / `_FABLE_MODEL_NAME` | Display name for that pinned model in the `/model` picker (defaults to the model ID) | Friendly labels for gateway/ARN model IDs | — |
| `ANTHROPIC_DEFAULT_OPUS_MODEL_DESCRIPTION` / `_SONNET_..._DESCRIPTION` / `_HAIKU_..._DESCRIPTION` / `_FABLE_..._DESCRIPTION` | Display description for that pinned model in the picker (defaults to `Custom <Tier> model`, or `(1M context)` variant if `[1m]` and `CLAUDE_CODE_DISABLE_1M_CONTEXT` is off) | Same as above | — |
| `ANTHROPIC_DEFAULT_OPUS_MODEL_SUPPORTED_CAPABILITIES` / `_SONNET_...` / `_HAIKU_...` / `_FABLE_...` | Comma list of capabilities (`effort`, `xhigh_effort`, `max_effort`, `thinking`, `adaptive_thinking`, `interleaved_thinking`) Claude Code should treat a pinned/gateway model ID as supporting, since pattern-based auto-detection can miss provider-specific IDs | Enable effort/thinking UI for a Bedrock ARN or gateway ID pattern-matching can't classify | — |
| `ANTHROPIC_SMALL_FAST_MODEL` | **Deprecated.** Haiku-class model for background tasks; superseded by `ANTHROPIC_DEFAULT_HAIKU_MODEL` | Legacy configs only | deprecated |
| `ANTHROPIC_SMALL_FAST_MODEL_AWS_REGION` | Overrides the AWS region for the Haiku-class model on Bedrock/Mantle; only takes effect when `ANTHROPIC_DEFAULT_HAIKU_MODEL` or `ANTHROPIC_SMALL_FAST_MODEL` is also set | Route background-model calls to a different Bedrock region | — |
| `ANTHROPIC_CUSTOM_MODEL_OPTION` | Adds one custom entry to the `/model` picker without replacing built-in aliases; skips ID validation | Test a gateway-only or non-standard model ID | — |
| `ANTHROPIC_CUSTOM_MODEL_OPTION_NAME` / `_DESCRIPTION` | Display name/description for that custom entry | Label the custom entry | — |
| `ANTHROPIC_CUSTOM_MODEL_OPTION_SUPPORTED_CAPABILITIES` | Capability list for the custom entry (same six values as the `_DEFAULT_*` family) | Enable effort/thinking for the custom entry | — |
| `CLAUDE_CODE_SUBAGENT_MODEL` | Default model for subagents, agent-team teammates, and workflow agents not otherwise assigned one. A per-invocation model or the agent definition's `model` field (incl. `inherit`) takes precedence unless `CLAUDE_CODE_SUBAGENT_MODEL_FORCE` is set | Run every unassigned delegate on Haiku for cost control | before v2.1.251 it also overrode explicit per-invocation/definition models |
| `CLAUDE_CODE_SUBAGENT_MODEL_FORCE` | Forces `CLAUDE_CODE_SUBAGENT_MODEL` onto every subagent/teammate/workflow agent, overriding per-invocation and definition `model` fields | Hard-pin all delegate work to one model regardless of what agent definitions request | v2.1.257 |
| `CLAUDE_CODE_ENABLE_GATEWAY_MODEL_DISCOVERY` | Populates the `/model` picker from a gateway's `/v1/models` endpoint when `ANTHROPIC_BASE_URL` points at one. Discovered models are still filtered by `availableModels` | Auto-surface gateway-hosted models instead of hand-listing them with `ANTHROPIC_CUSTOM_MODEL_OPTION` | — |
| `CLAUDE_CODE_DISABLE_LEGACY_MODEL_REMAP` | Stops automatic remap of Opus 4.0/4.1 to the current Opus version on the Anthropic API (no effect on Bedrock/Vertex/Foundry) | Intentionally pin an older Opus version | — |
| `CLAUDE_CODE_PROVIDER_MANAGED_BY_HOST` | Set by an embedding host platform: makes Claude Code ignore provider/model/auth variables (`CLAUDE_CODE_USE_BEDROCK`, `ANTHROPIC_BASE_URL`, `ANTHROPIC_API_KEY`, `ANTHROPIC_MODEL`, the `ANTHROPIC_DEFAULT_*_MODEL` family) in settings files, so the host's own routing/model config wins; a managed `availableModels` allowlist still applies unless the host supplies its own | Embed Claude Code in a product that manages its own model routing | — |
| `FALLBACK_FOR_ALL_PRIMARY_MODELS` | Makes every model stop retrying on repeated-overload errors when no `fallbackModel` chain is configured. **`0`/`false` still enables it** (unset to disable). Since v2.1.160 a configured fallback chain triggers on overload for any primary model regardless of this variable | Fail fast instead of long retry loops when no fallback chain is set | fallback-chain behavior changed v2.1.160 |

## Effort level & extended thinking

| Variable | What it does (relation to other vars) | Use cases | Date added |
|---|---|---|---|
| `CLAUDE_CODE_EFFORT_LEVEL` | Sets effort (`low`/`medium`/`high`/`xhigh`/`max`/`auto`). Takes precedence over `--effort`, `/effort`, `modelSettings`, `effortLevel` setting | Force low effort in a cost-sensitive CI job | — |
| `CLAUDE_CODE_ALWAYS_ENABLE_EFFORT` | Sends the `effort` parameter on every request even for models Claude Code doesn't recognize as effort-capable (useful behind a gateway); still excludes models that reject it outright (Claude 3, Sonnet 4.0/4.5, Opus 4.0/4.1, Haiku 4.5) | Force effort through an LLM gateway serving models under custom IDs | — |
| `CLAUDE_CODE_DISABLE_ADAPTIVE_THINKING` | On Opus 4.6/Sonnet 4.6 only, falls back to the fixed thinking budget set by `MAX_THINKING_TOKENS` instead of adaptive reasoning. No effect on Fable, Sonnet 5, or Opus 4.7+ (always adaptive) | Revert to fixed-budget thinking for older models | — |
| `CLAUDE_CODE_DISABLE_THINKING` | Omits the `thinking` parameter entirely (compatibility for proxies that reject it); model may still think by default. For an explicit off-switch on the Anthropic API use `MAX_THINKING_TOKENS=0` instead (ineffective on Fable) | Work around a proxy/gateway that 400s on the `thinking` field | — |
| `MAX_THINKING_TOKENS` | Fixed thinking-token budget; capped one below max output tokens, never below 1,024. `0` disables thinking on the Anthropic API except Fable (can't be turned off); on third-party providers `0` omits the parameter like `CLAUDE_CODE_DISABLE_THINKING` | Bound thinking spend on non-adaptive models | — |
| `DISABLE_INTERLEAVED_THINKING` | Stops sending the interleaved-thinking beta header | Work around a gateway that doesn't support interleaved thinking | — |

## Context window, compaction & extended context

| Variable | What it does (relation to other vars) | Use cases | Date added |
|---|---|---|---|
| `CLAUDE_CODE_AUTO_COMPACT_WINDOW` | Sets the auto-compact window in tokens (100K–1M, plain integer only). Takes precedence over `/autocompact`, `--autocompact`, and the `autoCompactWindow` setting; capped at the model's context window | Force earlier/later compaction in scripted or cloud sessions | — |
| `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE` | Sets what percentage (1–100) of the auto-compact window triggers compaction; can only lower the threshold, never raise it. Applies to main conversations and subagents | Compact at 50% instead of near-full to save headroom | — |
| `CLAUDE_CODE_MAX_CONTEXT_TOKENS` | Overrides the context window size Claude Code assumes for the active model; interacts with `CLAUDE_CODE_DISABLE_1M_CONTEXT` and `DISABLE_COMPACT` depending on whether the model ID is recognized as Claude | Correct the assumed window for a gateway-routed or unrecognized model ID | — |
| `CLAUDE_CODE_MAX_OUTPUT_TOKENS` | Caps output tokens per request (defaults to 32000 for unrecognized IDs); raising it shrinks the effective context window available before auto-compaction | Raise output ceiling for long generations at the cost of earlier compaction | — |
| `CLAUDE_CODE_DISABLE_1M_CONTEXT` | Removes 1M model variants from the picker and holds native-1M models (Sonnet 5, Fable) to a 200K window; auto-compaction then triggers at 200K, or the context-limit error fires if auto-compaction is off | Cap context for compliance-restricted deployments | — |
| `CLAUDE_CODE_DISABLE_UNKNOWN_MODEL_WINDOW_ENFORCEMENT` | Skips proactive auto-compaction for a model ID Claude Code doesn't recognize (e.g. a gateway alias); compacts only after the API rejects the request as too-long | Stop premature compaction on unrecognized gateway model IDs | v2.1.223 |
| `DISABLE_AUTO_COMPACT` | Disables automatic compaction; manual `/compact` still works. Overrides `autoCompactEnabled` setting | Take explicit manual control of when compaction runs | — |
| `DISABLE_COMPACT` | Disables all compaction, automatic and manual `/compact`. Also the condition under which `CLAUDE_CODE_MAX_CONTEXT_TOKENS` applies to a recognized Claude model ID | Fully disable compaction for a fixed-length scripted run | — |

## Prompt caching

| Variable | What it does (relation to other vars) | Use cases | Date added |
|---|---|---|---|
| `DISABLE_PROMPT_CACHING` | Disables prompt caching for all models; takes precedence over the per-tier `DISABLE_PROMPT_CACHING_*` variables | Debug caching-related behavior differences | — |
| `DISABLE_PROMPT_CACHING_HAIKU` / `_SONNET` / `_OPUS` / `_FABLE` | Disables prompt caching for that one model tier only | Isolate cache effects to one tier | — |
| `ENABLE_PROMPT_CACHING_1H` | Requests a 1-hour cache TTL instead of 5 minutes (billed at a higher rate). Overridden per-bucket by `CLAUDE_CODE_PROMPT_CACHE_TTL`/`CLAUDE_CODE_SUBAGENT_PROMPT_CACHE_TTL`, and by `FORCE_PROMPT_CACHING_5M` | Reduce cache-miss cost across long idle gaps | — |
| `ENABLE_PROMPT_CACHING_1H_BEDROCK` | **Deprecated.** Use `ENABLE_PROMPT_CACHING_1H` | — | deprecated |
| `FORCE_PROMPT_CACHING_5M` | Forces the 5-minute TTL even when 1-hour would otherwise apply; overrides `CLAUDE_CODE_PROMPT_CACHE_TTL`, `CLAUDE_CODE_SUBAGENT_PROMPT_CACHE_TTL`, `ENABLE_PROMPT_CACHING_1H`, and the matching settings keys | Avoid the higher 1-hour cache-write billing rate | — |
| `CLAUDE_CODE_PROMPT_CACHE_TTL` | `5m` or `1h` only; sets TTL for the main conversation (interactive/`-p`/SDK turns) | Pin main-conversation cache TTL independent of subagents | v2.1.242 |
| `CLAUDE_CODE_SUBAGENT_PROMPT_CACHE_TTL` | `5m` or `1h` only; sets TTL for subagents, workflows, background work | Pin delegate-work cache TTL separately from the main conversation | v2.1.242 |
| `CLAUDE_CODE_WEBFETCH_CACHE_TTL_MS` | How long WebFetch caches a fetched URL's response (default 900000ms/15min); read once per launch | Shorten/lengthen WebFetch's own response cache | v2.1.233 |

## Authentication & credentials

| Variable | What it does | Use cases | Date added |
|---|---|---|---|
| `ANTHROPIC_API_KEY` | API key sent as `X-Api-Key`; overrides a Pro/Max/Team/Enterprise subscription | Key-based auth instead of subscription login | — |
| `ANTHROPIC_AUTH_TOKEN` | Custom `Authorization: Bearer <value>` header | Custom bearer-token auth | — |
| `ANTHROPIC_AWS_API_KEY` | Workspace API key for Claude Platform on AWS; sent as `x-api-key`, outranks SigV4 | Auth to Claude Platform on AWS without SigV4 | — |
| `ANTHROPIC_AWS_WORKSPACE_ID` | Required workspace ID header for Claude Platform on AWS | Required Claude Platform on AWS config | — |
| `AWS_BEARER_TOKEN_BEDROCK` | Amazon Bedrock API key for authentication | Bedrock API-key auth | — |
| `ANTHROPIC_FOUNDRY_API_KEY` | API key for Microsoft Foundry | Foundry key auth | — |
| `ANTHROPIC_FOUNDRY_AUTH_TOKEN` | Bearer token for Foundry (e.g. Entra token); outranks `ANTHROPIC_FOUNDRY_API_KEY` and the Azure default credential chain | Foundry token-based auth | v2.1.203 |
| `ANTHROPIC_FEDERATION_RULE_ID` / `ANTHROPIC_ORGANIZATION_ID` | Set together to select Workload Identity Federation credentials, ranked above `/login` | Federation-based auth for automated environments | — |
| `ANTHROPIC_WORKSPACE_ID` | Workspace ID when a federation rule spans several workspaces | Disambiguate federation token exchange | — |
| `ANTHROPIC_PROFILE` | Name of the Anthropic profile to authenticate with | Multi-profile auth switching | — |
| `CLAUDE_CODE_OAUTH_REFRESH_TOKEN` / `CLAUDE_CODE_OAUTH_SCOPES` | Exchanges a refresh token directly for `claude auth login` instead of opening a browser; scopes required alongside the token | Provision auth in automated/headless environments | — |
| `CLAUDE_CODE_OAUTH_TOKEN` | OAuth access token; alternative to `/login`, outranks keychain credentials | SDK/automation auth without interactive login | — |
| `CLAUDE_CODE_API_KEY_HELPER_TTL_MS` | Refresh interval for `apiKeyHelper`-sourced credentials | Rotate short-lived helper-issued keys | — |
| `MCP_CLIENT_SECRET` | OAuth client secret for MCP servers needing pre-configured credentials | Non-interactive MCP OAuth setup | — |
| `MCP_OAUTH_CALLBACK_PORT` | Fixed OAuth callback port for MCP server auth | Pin a callback port instead of `--callback-port` | — |
| `CLAUDE_CODE_SKIP_ANTHROPIC_AWS_AUTH` / `_SKIP_BEDROCK_AUTH` / `_SKIP_MANTLE_AUTH` / `_SKIP_VERTEX_AUTH` / `_SKIP_FOUNDRY_AUTH` | Skip that provider's client-side auth (gateway signs requests itself); `_SKIP_FOUNDRY_AUTH` is ignored when a Foundry key/token is also set | Route through a gateway that handles provider auth | Foundry variant fixed in v2.1.203 |
| `CLAUDE_CODE_SKIP_AWS_CRED_CACHE` | Disables the in-process AWS credential cache, resolving the chain on every request | SSO profiles that must re-auth every call | v2.1.207 |
| `CLAUDE_CODE_AWS_CHAIN_RESOLVE_TIMEOUT_MS` | Timeout for the AWS default credential chain to resolve (default 60000) | Extend timeout for browser-based SSO+MFA | v2.1.207 |
| `CLAUDE_CODE_CLIENT_CERT` / `_CLIENT_KEY` / `_CLIENT_KEY_PASSPHRASE` | mTLS client cert/key/passphrase paths | mTLS-secured API endpoints | — |
| `CLAUDE_CODE_DISABLE_MTLS_RELOAD_ON_STALE_CONNECTION` | Stops re-reading rotated mTLS cert/key on connection-level failure | Avoid reload churn on flaky connections | v2.1.232 |
| `CLAUDE_CODE_CERT_STORE` | Comma list of CA sources (`bundled`, `system`); default `bundled,system` | Control which CA trust store validates TLS | — |

## Provider routing & third-party deployments

| Variable | What it does | Use cases | Date added |
|---|---|---|---|
| `ANTHROPIC_BASE_URL` | Overrides the API endpoint (proxy/gateway). Non-first-party hosts disable MCP tool search by default (`ENABLE_TOOL_SEARCH=true` to re-enable); disables Remote Control off `api.anthropic.com` | Route through an internal LLM gateway | Remote Control gating added v2.1.196 |
| `ANTHROPIC_AWS_BASE_URL` | Override Claude Platform on AWS endpoint (default `https://aws-external-anthropic.{region}.api.aws`) | Custom-region or gateway-routed Claude Platform on AWS | — |
| `ANTHROPIC_BEDROCK_BASE_URL` / `ANTHROPIC_BEDROCK_MANTLE_BASE_URL` | Override Bedrock / Bedrock Mantle endpoint URLs | Custom Bedrock endpoints or gateway routing | — |
| `ANTHROPIC_BEDROCK_REGION_PREFIX` | Cross-region inference profile prefix (`us`/`eu`/`apac`/`jp`/`au`/`global`) tried before the AWS-region-derived one; ignored in GovCloud | Force a specific Bedrock inference-profile region family | v2.1.224 |
| `ANTHROPIC_BEDROCK_SERVICE_TIER` | Bedrock service tier (`default`/`flex`/`priority`) sent as a header | Choose Bedrock inference priority | — |
| `ANTHROPIC_VERTEX_BASE_URL` | Override Google Cloud Agent Platform endpoint | Custom Vertex endpoints/gateway routing | — |
| `ANTHROPIC_VERTEX_PROJECT_ID` | GCP project ID for Vertex requests (overridden by `GCLOUD_PROJECT`/`GOOGLE_CLOUD_PROJECT`/credentials file) | Set Vertex project explicitly | — |
| `ANTHROPIC_FOUNDRY_BASE_URL` / `ANTHROPIC_FOUNDRY_RESOURCE` | Full base URL, or resource name, for the Foundry deployment (one or the other required) | Configure Microsoft Foundry endpoint | — |
| `CLAUDE_CODE_USE_ANTHROPIC_AWS` / `_USE_BEDROCK` / `_USE_FOUNDRY` / `_USE_MANTLE` / `_USE_VERTEX` | Selects that provider as the active backend | Switch backend provider | — |
| `ANTHROPIC_BETAS` | Extra `anthropic-beta` header values; works with subscription auth (unlike `--betas`, which needs an API key) | Opt into a beta before Claude Code natively supports it | — |
| `ANTHROPIC_CUSTOM_HEADERS` | Custom `Name: Value` headers, newline-separated | Inject gateway-required headers | v2.1.227 |
| `CLAUDE_CODE_PROXY_RESOLVES_HOSTS` | Lets the proxy perform DNS resolution instead of the caller | Proxy-side hostname resolution | — |
| `CLAUDE_CODE_ATTRIBUTION_HEADER` | `0` omits the client-version/prompt-fingerprint attribution block from the system prompt start; direct-API caching unaffected either way | Avoid gateway cache-key pollution or forwarding issues | pre-v2.1.181 token behavior differs |
| `CLAUDE_CODE_PROPAGATE_TRACEPARENT` | Propagates W3C trace context (`traceparent` header + `TRACEPARENT` env for subprocesses) when `ANTHROPIC_BASE_URL` points at a custom proxy; on by default only for direct Anthropic API | Distributed tracing through a custom proxy | v2.1.152 |
| `HTTP_PROXY` / `HTTPS_PROXY` / `NO_PROXY` | Standard proxy configuration | Corporate proxy setups | — |
| `CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS` | Strips Anthropic-specific `anthropic-beta` request headers and beta tool-schema fields (`defer_loading`, `eager_input_streaming`) from API requests; also disables MCP tool search (all MCP tools load upfront) even if `ENABLE_TOOL_SEARCH` is set, unless managed settings on v2.1.227+ keep tool search on | Work around a proxy gateway that rejects unrecognized `anthropic-beta` headers or extra schema fields | tool-search exception v2.1.227 |
| `CLAUDE_CODE_ENABLE_AUTO_MODE` | Accepted for compatibility, now a no-op; auto mode is on by default on every provider. In v2.1.158–v2.1.206 it was required to enable auto mode on Bedrock/Vertex/Foundry/Claude apps gateway | Legacy config cleanup only | superseded v2.1.207 |
| `CLAUDE_CODE_DISABLE_ADMIN_ENV_UNION` | Stops merging managed-settings `env` blocks per key across admin sources, so only the highest-priority source's whole `env` block applies (pre-v2.1.223 behavior). Must be set in the launching environment; a copy delivered through a settings `env` block is ignored | Revert to single-source managed `env` block resolution | v2.1.223 |

## Vertex region overrides (per model)

| Variable | What it does | Use cases | Date added |
|---|---|---|---|
| `VERTEX_REGION_CLAUDE_3_5_HAIKU`, `_3_5_SONNET`, `_3_7_SONNET`, `_4_0_OPUS`, `_4_0_SONNET`, `_4_1_OPUS`, `_4_5_OPUS`, `_4_5_SONNET`, `_4_6_OPUS`, `_4_6_SONNET`, `_4_7_OPUS`, `_HAIKU_4_5` | Overrides the Google Cloud Agent Platform region for that specific Claude version | Route a specific model version to a different Vertex region | — |
| `VERTEX_REGION_CLAUDE_4_8_OPUS` | Same, for Opus 4.8 | — | v2.1.154 |
| `VERTEX_REGION_CLAUDE_5_OPUS` | Same, for Opus 5 | — | v2.1.219 |
| `VERTEX_REGION_CLAUDE_5_SONNET` | Same, for Sonnet 5 | — | v2.1.197 |
| `VERTEX_REGION_CLAUDE_FABLE_5` | Same, for Fable 5 | — | v2.1.170 |
| `VERTEX_REGION_CLAUDE_FABLE_5_1` | Same, for Fable 5.1 | — | v2.1.255 |

## Networking, timeouts & streaming watchdogs

| Variable | What it does | Use cases | Date added |
|---|---|---|---|
| `API_TIMEOUT_MS` | Per-request API timeout (default 600000ms/10min, max 2147483647) | Slow networks/proxies | — |
| `API_FORCE_IDLE_TIMEOUT` | Overrides the 5-min body-idle timeout on streaming responses; `0` off, `1` on for every provider; independent of the stream watchdogs | Tolerate a slow gateway/local model with long pauses between chunks | v2.1.169 |
| `CLAUDE_STREAM_IDLE_TIMEOUT_MS` | Timeout before event-/byte-level stream watchdogs close a stalled connection (min 300000ms when set explicitly); `CLAUDE_BYTE_STREAM_IDLE_TIMEOUT_MS` takes precedence for the byte-level watchdog | Tune stall detection for slow/thinking-heavy responses | — |
| `CLAUDE_BYTE_STREAM_IDLE_TIMEOUT_MS` | Timeout specifically for the byte-level watchdog, overriding `CLAUDE_STREAM_IDLE_TIMEOUT_MS` for that one; clamped 10s–30min | Separate byte- vs event-level stall tolerance | v2.1.210 |
| `CLAUDE_STREAM_FIRST_BYTE_TIMEOUT_MS` | Deadline for the first response byte of a streaming request | Detect a hung connection before any bytes arrive | v2.1.242 |
| `CLAUDE_ENABLE_STREAM_WATCHDOG` | Force on/off the event-level idle watchdog (on by default for all providers since v2.1.196) | Disable stall detection for an unusual gateway | — |
| `CLAUDE_ENABLE_BYTE_WATCHDOG` | Force on/off the byte-level idle watchdog and its first-byte deadline (on by default for direct API/Claude Platform on AWS and gateway streaming since v2.1.222) | Same, byte-level | v2.1.222 (gateway default) |
| `CLAUDE_ENABLE_BYTE_WATCHDOG_BEDROCK` | Enables the byte-level watchdog specifically on Bedrock's event-stream responses (off by default) | Byte-level stall detection on Bedrock | — |
| `CLAUDE_CODE_DISABLE_BEDROCK_CONTENT_TYPE_DEFAULT` / `_CONTENT_TYPE_GUARD` | Control how Claude Code treats a Bedrock streaming response's `Content-Type` header (assume vs. guard against gateway rewriting) | Diagnose/work around a gateway altering Bedrock's stream content-type | v2.1.239 / v2.1.208 |
| `CLAUDE_CODE_DISABLE_NONSTREAMING_FALLBACK` | Disables falling back to non-streaming when a streaming request fails mid-stream | Avoid duplicate tool execution from a broken proxy fallback | — |
| `CLAUDE_CODE_ENABLE_FINE_GRAINED_TOOL_STREAMING` | Controls whether tool-call inputs stream as generated vs. arrive all at once; on by default on Anthropic API, off by default on Foundry/gateways | Avoid a "hanging" appearance on large tool inputs | — |
| `CLAUDE_CODE_MAX_RETRIES` | Retries for failed API requests (default 10, capped 15 unless `CLAUDE_CODE_RETRY_WATCHDOG` is set) | Tune retry count for flaky networks | cap raised v2.1.186 |
| `CLAUDE_CODE_RETRY_WATCHDOG` | Unattended-session mode: retries 429/529 indefinitely (except spend-limit 429s), raises other transient-error retries to 300 and removes the 15-cap on `CLAUDE_CODE_MAX_RETRIES` | CI/eval harnesses that must wait out outages | v2.1.186 (behavior change v2.1.199, v2.1.239) |
| `CLAUDE_CODE_CONNECT_TIMEOUT_MS` | **Removed/no-op** since v2.1.186; use `API_TIMEOUT_MS` and `CLAUDE_STREAM_FIRST_BYTE_TIMEOUT_MS` instead | — | removed v2.1.186 |

## Memory, CLAUDE.md, skills & instructions loaded into context

| Variable | What it does | Use cases | Date added |
|---|---|---|---|
| `CLAUDE_CODE_DISABLE_CLAUDE_MDS` | Prevents loading any CLAUDE.md memory file (user/project/auto) | Run with zero project instructions loaded | — |
| `CLAUDE_CODE_ADDITIONAL_DIRECTORIES_CLAUDE_MD` | Loads CLAUDE.md/`.claude/rules/*.md`/`CLAUDE.local.md` from `--add-dir` directories too (off by default) | Pull in instructions from an added directory | — |
| `CLAUDE_CODE_DISABLE_AUTO_MEMORY` | Disables auto memory creation/loading; `0` force-enables it even under `--bare`/`autoMemoryEnabled: false` | Turn off (or force on) the auto-memory feature | — |
| `CLAUDE_CODE_DISABLE_BUNDLED_SKILLS` | Removes bundled skills/workflows entirely (built-ins like `/init` stay typable but hidden from the model); plugin/`.claude/skills`/`.claude/commands` skills unaffected | Strip built-in skill surface for a minimal deployment | — |
| `CLAUDE_CODE_DISABLE_POLICY_SKILLS` | Skips loading skills from the system-wide managed skills directory | Containers/CI that shouldn't load operator-provisioned skills | — |
| `CLAUDE_CODE_SYNC_SKILLS` | Downloads enabled claude.ai skills into `~/.claude/skills/synced/`, resyncs every 10 min; `-p` mode only, needs claude.ai auth | Give a non-interactive session your claude.ai skill set | folder moved to `synced/` in v2.1.227 |
| `CLAUDE_CODE_SYNC_SKILLS_WAIT_TIMEOUT_MS` | How long the first query waits for the initial skill list from `CLAUDE_CODE_SYNC_SKILLS` (default 5000) | Bound first-query latency for skill sync | — |
| `CLAUDE_CODE_SYNC_SKILLS_INSTALL_TIMEOUT_MS` | How long a mid-session skills resync (same feature) may take (default 30000) | Bound mid-session resync latency | — |
| `SLASH_COMMAND_TOOL_CHAR_BUDGET` | Character budget for skill metadata shown to the Skill tool (scales at 1% of context window, 8,000-char fallback) | Control how much skill-list metadata competes for context | — |
| `CLAUDE_CODE_DISABLE_GIT_INSTRUCTIONS` | Removes built-in commit/PR workflow instructions and the git-status snapshot from the system prompt; outranks `includeGitInstructions` setting | Replace built-in git guidance with your own skill | — |
| `CLAUDE_CODE_DISABLE_CFC_PROMPT` | Keeps Claude-in-Chrome tools but removes the Chrome system-prompt section and its bundled skill | Host supplies its own browser-tool guidance | v2.1.257 |
| `CLAUDE_CODE_SIMPLE_SYSTEM_PROMPT` | Shorter system prompt + abbreviated tool descriptions on any model; `0`/`false`/`no`/`off` opts out even where an experiment would enable it | Reduce fixed context overhead from the system prompt | — |
| `CLAUDE_CODE_SIMPLE` (`--bare`) | Minimal prompt + Bash/read/edit tools only; disables auto-discovery of hooks, skills, custom commands, subagents, plugins, MCP servers, auto memory, and CLAUDE.md; `--add-dir` skills still load | Strip everything down to a bare agent loop | — |
| `CLAUDE_CODE_SAFE_MODE` (`--safe-mode`) | Disables CLAUDE.md, skills, plugins, hooks, MCP servers, custom commands/agents, output styles, workflows, themes, keybindings, statusline/file-suggestion commands, LSP servers, and auto memory; managed-settings-delivered hooks/statusline/policy MCP servers still apply | Troubleshoot a broken customization by ruling all of them out | — |
| `CLAUDE_CODE_NEW_INIT` | Makes `/init` run an interactive setup flow asking which files (CLAUDE.md, skills, hooks) to generate, instead of auto-generating CLAUDE.md silently | Curate what `/init` writes | — |
| `CLAUDE_CONFIG_DIR` | Overrides the config root (default `~/.claude`); all settings, session history, and plugins — and therefore which CLAUDE.md/rules/skills load — live under this path. Settable in shell/user/managed settings; ignored in project/local settings | Run multiple accounts/configs side by side | — |
| `ENABLE_TOOL_SEARCH` | Controls whether MCP tool definitions defer (load on demand) or load upfront into context; `auto`/`auto:N` load upfront under a context-fraction threshold | Control how much MCP tool-schema content competes for context | — |
| `CLAUDE_CODE_ENABLE_APPEND_SUBAGENT_PROMPT` | Appends extra text to the end of every non-forked subagent's system prompt; normally set automatically by `--append-subagent-system-prompt[-file]` | Inject a standing instruction into every subagent's context | v2.1.205 |
| `CLAUDE_CODE_ENABLE_BACKGROUND_PLUGIN_REFRESH` | Refreshes plugin state (which changes the system prompt) at turn boundaries in `-p` mode after a background plugin install; off by default because it invalidates prompt caching for that turn | Pick up a newly-installed plugin mid-session at the cost of a cache miss | — |
| `CLAUDE_CODE_DISABLE_ATTACHMENTS` | Disables attachment processing: `@`-mentioned files are sent as plain text instead of being expanded into file content in context | Stop `@file` mentions from pulling file content into context | — |

## Hooks & subprocess environment

| Variable | What it does | Use cases | Date added |
|---|---|---|---|
| `CLAUDE_CODE_SUBPROCESS_ENV_SCRUB` | Strips recognized credentials (Anthropic, cloud provider, package-registry-embedded) from Bash/hook/MCP-stdio subprocess environments; on Linux also isolates Bash subprocesses in a PID namespace (so `ps`/`pgrep`/`kill` can't see host processes) | Reduce secret-exfiltration risk from prompt injection in tool calls | `claude-code-action` sets it automatically with `allowed_non_write_users` |
| `CLAUDE_CODE_MCP_ALLOWLIST_ENV` | Spawns stdio MCP servers with only a safe baseline env plus the server's own configured `env`, instead of inheriting the shell environment | Prevent an MCP server from reading your full shell env | — |
| `CLAUDE_CODE_SCRIPT_CAPS` | JSON map of command-substring → call-limit-per-session, enforced alongside `CLAUDE_CODE_SUBPROCESS_ENV_SCRUB`; substring-matched, defense-in-depth only | Cap how many times a sensitive script (e.g. `deploy.sh`) can run per session | — |
| `CLAUDE_ENV_FILE` | Path to a shell script Claude Code sources before every Bash command in the same shell process; also populated dynamically by `SessionStart`, `Setup`, `CwdChanged`, and `FileChanged` hooks | Persist a virtualenv/conda activation across Bash calls | — |
| `CLAUDE_EFFORT` | Exported into Bash/hook subprocesses reflecting the current effort level (`low`/`medium`/`high`/`xhigh`/`max`; ultracode reports as `xhigh`); matches the `effort.level` hook JSON field | Let a hook branch on the active effort level | — |
| `CLAUDE_CODE_STOP_HOOK_BLOCK_CAP` | Max consecutive times a `Stop`/`SubagentStop` hook may block turn-end before Claude Code overrides it (default 8; `0` disables the cap) | Prevent a misbehaving Stop hook from looping forever | — |
| `CLAUDE_CODE_SESSIONEND_HOOKS_TIMEOUT_MS` | Time budget for `SessionEnd` hooks on exit/`/clear`/`/resume` switch (default 1.5s, auto-raised to the highest configured per-hook `timeout`, capped 60s; plugin-hook timeouts don't raise it) | Give a slow cleanup `SessionEnd` hook more time | — |
| `CLAUDE_CODE_DISABLE_PERMISSION_PROMPT_NOTIFY_HOOKS` | Stops `Notification` hooks from firing for unanswered permission prompts when Claude Code routes them through the SDK's `canUseTool` callback (Claude Desktop, VS Code extension); no effect in terminal sessions | Avoid duplicate notification handling when a host app already surfaces the prompt | v2.1.233 |
| `CLAUDE_CODE_RESUME_PROMPT` | Overrides the injected continuation message on mid-turn resume (default "Continue from where you left off.") | Give a resumed long-running agent a more directive boot message | — |
| `CLAUDE_CODE_RESUME_INTERRUPTED_TURN` | Auto-resumes a session that ended mid-turn (SDK mode) without the SDK re-sending the prompt | Seamless SDK resume after an interrupted turn | behavior fixed v2.1.221 |
| `CLAUDE_CODE_RESUME_INTERRUPTED_TURN_MAX_AGE_MS` | Max age of the last transcript message for the above auto-resume (and the `CLAUDE_CODE_RESUME_PROMPT` injection) to still fire; unset/`0` = no bound | Skip auto-resume against a stale transcript | v2.1.211 |

## Subagents, agent teams & workflows

| Variable | What it does | Use cases | Date added |
|---|---|---|---|
| `CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS` | Cap on subagents running at once in a session (default 20) | Limit fan-out concurrency | v2.1.217 |
| `CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH` | How many subagent layers may nest below the main conversation (default 3; `1` disables nesting) | Bound recursive delegation depth | v2.1.217 (default raised to 3 in v2.1.219) |
| `CLAUDE_CODE_MAX_SUBAGENTS_PER_SESSION` | **Removed/no-op** since v2.1.224; use the concurrent and depth limits instead | — | removed v2.1.224 |
| `CLAUDE_CODE_MAX_TOOL_USE_CONCURRENCY` | Max read-only tools + subagents running in parallel (default 10) | Tune parallelism vs. resource use | — |
| `CLAUDE_ASYNC_AGENT_STALL_TIMEOUT_MS` | Stall timeout for subagents (default 600000ms/10min); rises automatically if `CLAUDE_STREAM_IDLE_TIMEOUT_MS` is raised | Detect a hung subagent | — |
| `CLAUDE_SUBAGENT_BG_SHELL_MAX_MS` | Max lifetime for a background shell command a subagent started (default 3600000ms/60min); `0` restores the default rather than removing the cap | Bound long-running subagent-launched background shells | — |
| `CLAUDE_CODE_FORK_SUBAGENT` | Controls fork mode (Claude spawning forked subagents itself); on by default in interactive sessions only; `1`/`0` force it in any session type | Enable/disable self-directed forking in `-p`/SDK sessions | interactive default v2.1.232 |
| `CLAUDE_CODE_FORWARD_SUBAGENT_TEXT` | Emits subagent text/thinking blocks in `claude -p --output-format stream-json`, same as `--forward-subagent-text` | Surface subagent narration in a harness that can't pass the flag | v2.1.211 |
| `CLAUDE_CODE_DISABLE_EXPLORE_PLAN_AGENTS` | Disables the built-in Explore/Plan subagents (search tools/general-purpose subagent and direct-read plan mode used instead); custom agents named `Explore`/`Plan` unaffected | Remove built-in exploration agents in favor of custom ones | v2.1.198 |
| `CLAUDE_AGENT_SDK_DISABLE_BUILTIN_AGENTS` | SDK-only, non-interactive mode: disables all built-in subagent types including `general-purpose`, so an Agent call without `subagent_type` fails | Give SDK users a completely blank subagent slate | — |
| `CLAUDE_AGENT_SDK_MCP_NO_PREFIX` | Skips the `mcp__<server>__` prefix on SDK-created MCP server tool names | SDK integrations needing original tool names | — |
| `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS` | Enables agent teams (experimental, off by default) | Try multi-agent teams | — |
| `CLAUDE_CODE_TEAM_TEARDOWN_PARK_TIMEOUT_MS` | How long a non-interactive session waits at exit for its agent team to tear down (1000–60000, default 10000) | Bound teardown wait in scripted runs | v2.1.206 |
| `CLAUDE_CODE_DISABLE_WORKFLOWS` | Disables workflows entirely | Remove dynamic-workflow orchestration | — |
| `CLAUDE_CODE_WORKFLOW_PREFIX_STAGGER_MS` | Upper bound on how long a workflow agent waits for a same-prefix sibling to start, so a fan-out reads a cached prompt prefix (default 5000; `0` disables; never waits if `DISABLE_PROMPT_CACHING` is set) | Improve cache hit rate on workflow fan-outs | v2.1.229 |
| `CLAUDE_AUTO_BACKGROUND_TASKS` | Force-enables auto-backgrounding of long subagent tasks (~2min) and, in `-p` mode on v2.1.212+, long MCP tool calls | Auto-background slow delegate work | — |
| `CLAUDE_CODE_AUTO_BACKGROUND_WORKER_CHECKIN_SECONDS` | Reminder interval (1–86400s) for Claude to check on still-running background subagents, when the above is on | Periodic check-ins on backgrounded work | v2.1.248 |
| `CLAUDE_CODE_DISABLE_BACKGROUND_TASKS` | Disables all backgrounding: `run_in_background`, auto-backgrounding, Ctrl+B | Force everything to run in the foreground | — |
| `CLAUDE_CODE_DISABLE_AGENT_VIEW` | Turns off background agents/agent view (`claude agents`, `--bg`, `/background`, supervisor); same as `disableAgentView` setting | Remove the background-agent surface | — |
| `CLAUDE_CODE_DISABLE_BG_EXIT_HANDOFF` | Stops background shells/workflows/subagents from handing off to a session's next process on supervisor restart (only that handoff; `←`/`/background` still carries work over) | Prevent in-flight work surviving a supervisor restart | v2.1.196 |
| `CLAUDE_DISABLE_ADOPT` | Stops in-flight background work from carrying over when you background a session with `←`/`/background` (asks for confirmation first) | Discard rather than adopt background work on backgrounding | v2.1.195 |
| `CLAUDE_CODE_DISABLE_BG_SHELL_PRESSURE_REAP` | Stops Claude Code from killing background shells on OS memory-pressure signals (macOS/Linux only, after 30min idle) | Keep long background shells alive under memory pressure | v2.1.193 |
| `CLAUDE_CODE_PRINT_BG_WAIT_CEILING_MS` | Ceiling on idle waiting for background subagents/workflows after the final turn in `-p` mode (default 600000ms/10min; `0` waits indefinitely) | Bound how long a headless run waits for background work to finish | v2.1.182 |
| `CLAUDE_CODE_GOAL_CHECKIN_MINUTES` | Minutes background work can keep an active goal waiting before Claude checks on it (default 30; `0` off; max 10080) | Tune goal check-in cadence | v2.1.234 |

## MCP servers

| Variable | What it does | Use cases | Date added |
|---|---|---|---|
| `MCP_CONNECTION_NONBLOCKING` | `0` makes startup wait for MCP servers to connect before the first query (default: non-blocking) | Guarantee MCP tools are ready on turn one | — |
| `MCP_CONNECT_TIMEOUT_MS` | How long blocking MCP startup waits before snapshotting the tool list (default 5000) | Bound blocking-connect wait | — |
| `MCP_TIMEOUT` | Timeout for MCP server startup (default 30000) | Slow-starting MCP servers | — |
| `MCP_TOOL_TIMEOUT` | Timeout for MCP tool execution (default ~28h); HTTP/SSE/connector servers also cap per-request at 60s unless raised above 60000 | Long-running MCP tool calls | — |
| `CLAUDE_CODE_MCP_TOOL_IDLE_TIMEOUT` | Idle timeout when an MCP server sends no response/progress; overrides per-transport defaults (300000 network, 1800000 stdio); `0` disables | Abort a truly stuck MCP call without waiting the full `MCP_TOOL_TIMEOUT` | v2.1.187 |
| `CLAUDE_CODE_MCP_AUTO_BACKGROUND_MS` | Elapsed time before a still-running MCP tool call auto-backgrounds (default 120000; `0` off) | Keep the session responsive during a slow MCP call | v2.1.212 |
| `MAX_MCP_OUTPUT_TOKENS` | Max tokens in MCP tool responses (warns above 10,000; default 25000); tools declaring `anthropic/maxResultSizeChars` use that instead for text | Cap MCP response size | — |
| `MCP_SERVER_CONNECTION_BATCH_SIZE` / `MCP_REMOTE_SERVER_CONNECTION_BATCH_SIZE` | Max local (stdio) / remote (HTTP/SSE) servers connected in parallel at startup (defaults 3 / 20) | Tune startup connection parallelism | — |
| `MCP_DISCOVERY_CACHE` | Turns the MCP discovery cache on/off (off by default unless a gradual rollout enabled it) | Speed up repeat connections to known remote servers | cache-off default since v2.1.238 |
| `MCP_DISCOVERY_CACHE_TTL_S` / `_MAX_STALE_S` / `_STRIKES` | TTL before refresh (default 900), max staleness before discard (default 14400, capped 7 days), and consecutive-failure tolerance (default 1) for cache entries | Tune discovery-cache freshness/resilience | caps added v2.1.238 |
| `MCP_SDK_GENERATION` | Pins the MCP client runtime to `v1` or `v2`; `v2` is default on v2.1.232+ except stated exceptions | Force the legacy v1 runtime for compatibility | v2.1.218 |
| `MCP_PROTOCOL_NEGOTIATION` | `auto` probes servers for the newer MCP protocol revision; `legacy` skips the probe | Control MCP protocol-revision negotiation | v2.1.221 |
| `ENABLE_CLAUDEAI_MCP_SERVERS` | `false` stops fetching claude.ai MCP servers (on by default for logged-in users) | Disable claude.ai-connector MCP servers | — |

## Plugins & marketplace

| Variable | What it does | Use cases | Date added |
|---|---|---|---|
| `CLAUDE_CODE_PLUGIN_CACHE_DIR` | Overrides the plugins root directory (parent of the cache, default `~/.claude/plugins`) | Relocate plugin storage | — |
| `CLAUDE_CODE_PLUGIN_SEED_DIR` | Path(s) to read-only plugin seed directories (`:`/`;`-separated) | Bundle pre-populated plugins into a container image | — |
| `CLAUDE_CODE_PLUGIN_GIT_TIMEOUT_MS` | Timeout for plugin install/update git operations (default 120000) | Large repos / slow networks | — |
| `CLAUDE_CODE_PLUGIN_PREFER_HTTPS` | Clones `owner/repo` shorthand over HTTPS instead of SSH | CI/containers without an SSH key | — |
| `CLAUDE_CODE_PLUGIN_KEEP_MARKETPLACE_ON_FAILURE` | Skips re-clone and keeps the existing cache when `git pull` fails | Offline/airgapped environments | — |
| `CLAUDE_CODE_DISABLE_OFFICIAL_MARKETPLACE_AUTOINSTALL` | Permanently skips auto-registering the official marketplace (checked once, at first interactive launch) | Prevent auto-registration on managed machines | — |
| `CLAUDE_CODE_SYNC_PLUGIN_INSTALL` | In `-p` mode, waits for plugin install before the first query (combine with the timeout below) | Guarantee plugins are ready before headless run starts | — |
| `CLAUDE_CODE_SYNC_PLUGIN_INSTALL_TIMEOUT_MS` | Timeout for the above synchronous install | Bound that wait | — |
| `FORCE_AUTOUPDATE_PLUGINS` | Forces plugin auto-updates even with `DISABLE_AUTOUPDATER` set | Keep plugins current while freezing the CLI version | — |

## Bash/PowerShell/shell tool behavior

| Variable | What it does | Use cases | Date added |
|---|---|---|---|
| `BASH_DEFAULT_TIMEOUT_MS` / `BASH_MAX_TIMEOUT_MS` | Default (120000) / model-settable ceiling (600000, floor = larger of the two) for Bash commands | Tune long-running-command timeouts | — |
| `BASH_MAX_OUTPUT_LENGTH` | Max chars of Bash output read back (default 30000, max 150000); ignored if `bashOutputMaxChars` setting is set | Read more/less of a command's output | — |
| `CLAUDE_CODE_SHELL` | Path to the `bash`/`zsh` binary Bash tool commands run under | Pin a non-default shell binary | — |
| `CLAUDE_CODE_SHELL_PREFIX` | Wraps every spawned shell command (Bash calls, hooks, statusline, stdio MCP startup) in a logging/auditing prefix | Audit or log every shell command Claude Code runs | — |
| `CLAUDE_BASH_MAINTAIN_PROJECT_WORKING_DIR` | Returns to the original cwd after each Bash/PowerShell command in the main session | Prevent `cd` state leaking between tool calls | — |
| `CLAUDE_CODE_PROCESS_WRAPPER` | Launches processes Claude Code starts from its own binary (e.g. the agent-view background service) through a corporate launcher argv prefix. Must be set in the `env` block of user or managed settings, never as a shell export or in project/local settings, so the detached background service inherits it. Equivalent to the `processWrapper` setting (this variable wins if both set); ignored on Windows | Route Claude Code's spawned processes through a corporate launcher/wrapper | v2.1.208 (`processWrapper` setting needs v2.1.210) |
| `CLAUDE_CODE_USE_POWERSHELL_TOOL` | Enables the PowerShell tool (platform/Git-Bash-dependent defaults) | Run PowerShell natively instead of via Git Bash | — |
| `CLAUDE_CODE_POWERSHELL_RESPECT_EXECUTION_POLICY` | Stops passing `-ExecutionPolicy Bypass` to spawned PowerShell | Respect the machine's execution policy | — |
| `CLAUDE_CODE_GIT_BASH_PATH` | Path to `bash.exe` on Windows when not on `PATH` | Point at a non-standard Git Bash install | before v2.1.219, an invalid path exited at startup |
| `CLAUDE_CODE_TOOL_MEMORY_LIMIT` | Caps memory Bash/PowerShell(/Monitor) tool commands can use, Linux/WSL only | Prevent a runaway command from exhausting host memory | v2.1.233 (Monitor coverage v2.1.246) |
| `CLAUDE_CODE_TOOL_MEMORY_CGROUP_EXCLUDE` | Excludes process kinds (e.g. `mcp`, `lsp`) from the memory cap above; Bash/PowerShell/Monitor always capped | Exempt long-lived helper processes from the memory cap | v2.1.246 |
| `CLAUDE_CODE_PERFORCE_MODE` | Fails Edit/Write/NotebookEdit with a `p4 edit` hint when the target lacks the owner-write bit | Prevent bypassing Perforce change tracking | — |
| `CLAUDE_CODE_BS_AS_CTRL_BACKSPACE` | Whether `0x08`/`^H` reads as Backspace or Ctrl+Backspace | Fix backspace behavior in a specific terminal | — |

## File/glob/web search tool limits

| Variable | What it does | Use cases | Date added |
|---|---|---|---|
| `CLAUDE_CODE_FILE_READ_MAX_OUTPUT_TOKENS` | Overrides the default token limit for file reads | Read larger files in full | — |
| `CLAUDE_CODE_GLOB_HIDDEN` | `false` excludes dotfiles from Glob results (included by default) | Hide dotfiles from Glob only | — |
| `CLAUDE_CODE_GLOB_NO_IGNORE` | `false` makes Glob respect `.gitignore` (ignored by default) | Restrict Glob to non-gitignored files | — |
| `CLAUDE_CODE_GLOB_TIMEOUT_SECONDS` | Glob discovery timeout (20s default, 60s on WSL) | Tune Glob timeout on slow filesystems | — |
| `CLAUDE_CODE_USE_NATIVE_FILE_SEARCH` | Uses Node.js file APIs instead of ripgrep for discovering commands/subagents/output styles (not Grep/file search) | Work around a blocked/unavailable bundled ripgrep | — |
| `USE_BUILTIN_RIPGREP` | `0` uses system-installed `rg` instead of the bundled one | Use a system ripgrep build | — |
| `CLAUDE_CODE_MAX_WEB_SEARCHES_PER_SESSION` | Cap on total WebSearch calls per session (default 200) | Bound web-search spend/usage | v2.1.212 |
| `CLAUDE_CODE_WEBFETCH_CACHE_TTL_MS` | See Prompt caching section above | — | v2.1.233 |
| `TASK_MAX_OUTPUT_LENGTH` | Max chars of a background task's output the `TaskOutput` tool keeps (default 32000, max 160000); ignored if `taskOutputMaxChars` is set | Read more/less of a backgrounded task's output | — |
| `CLAUDE_CODE_TASK_LIST_ID` | Shares a task list across sessions via a common ID | Coordinate multiple Claude Code instances on one task list | — |
| `CLAUDE_CODE_ENABLE_TASKS` | Selects Task tools (`TaskCreate`/`TaskUpdate`/`TaskGet`/`TaskList`) vs. legacy `TodoWrite` (`0`) | Fall back to the legacy todo tool | — |
| `CLAUDE_CODE_ENABLE_TODO_TOOLS` | Adds task-tracking tools on models that otherwise lack them | Get task tools on an unlisted model | v2.1.233 |

## Session, resume, persistence & multi-config

| Variable | What it does | Use cases | Date added |
|---|---|---|---|
| `CLAUDE_CODE_SESSION_ID` | Exported to Bash/hook/MCP-stdio subprocesses with the current session ID | Correlate external scripts with the launching session | — |
| `CLAUDE_CODE_CHILD_SESSION` | Set to `1` by Claude Code itself in every subprocess it spawns (not by IDE extensions); excludes a nested `claude` TUI from `--resume`/history/`claude agents` unless `CLAUDE_CODE_FORCE_SESSION_PERSISTENCE=1` | Reliably detect a nested vs. top-level session | v2.1.172 |
| `CLAUDECODE` | Set to `1` in every Claude-Code-spawned subprocess, and by IDE extensions in their integrated terminals | Detect "running inside Claude Code" from any subprocess | — |
| `CLAUDE_CODE_FORCE_SESSION_PERSISTENCE` | Forces transcript/history/`claude agents` registration even when launched from inside another Claude Code session | Fix a genuine top-level session misclassified as nested (e.g. via `screen`) | tmux case auto-handled since v2.1.178 |
| `CLAUDE_CODE_SKIP_PROMPT_HISTORY` | Skips writing prompt history/transcripts to disk; session won't appear in `--resume`/`--continue`/history | Ephemeral scripted sessions that shouldn't persist | — |
| `CLAUDE_PID` | Claude Code's own PID, exported to Bash/hook subprocesses | Identify/signal the parent Claude Code process from a script | v2.1.214 |
| `CLAUDE_CODE_EXIT_AFTER_STOP_DELAY` | ms to wait after the query loop idles before auto-exiting (SDK mode) | Automated scripts using SDK mode | — |
| `CLAUDE_CONFIG_DIR` | See Memory section above (also governs where session history/transcripts live) | Multi-account setups | — |
| `CLAUDE_CODE_PROJECT_DIR_NAME` | With `CLAUDE_CONFIG_DIR` set, names the `projects/` subdirectory for transcripts/auto memory instead of deriving it from the cwd; shell-only, never from a settings `env` block | Predictable transcript storage path for multi-tenant setups | v2.1.234 |
| `CLAUDE_CODE_TMPDIR` | Overrides the temp directory root for Claude Code's own temp files | Redirect temp files off a constrained `/tmp` | sandboxed-fallback behavior added v2.1.161 |
| `CLAUDE_CODE_RESTRICTED` | Starts the session in restricted mode (same as `--restricted`); ignored in a settings `env` block | Force restricted mode from the launch environment | v2.1.248 |

## Remote Control & cross-session messaging

| Variable | What it does | Use cases | Date added |
|---|---|---|---|
| `CLAUDE_CODE_BRIDGE_SESSION_ID` | Exported to Bash/hook subprocesses while a Remote Control connection is active; matches the session's `claude.ai/code` URL ID | Link a script's output back to the Remote-Control-connected session | v2.1.199 |
| `CLAUDE_CODE_REMOTE` / `CLAUDE_CODE_REMOTE_SESSION_ID` | `true` when running as a cloud session; the cloud session's own ID | Detect a cloud session and link back to its transcript | — |
| `CLAUDE_REMOTE_CONTROL_SESSION_NAME_PREFIX` | Prefix for auto-generated Remote Control session names (default: hostname) | Customize auto-generated session names | — |
| `CLAUDE_CLIENT_PRESENCE_FILE` | Path an external screen-lock listener creates/deletes; while present, skips Remote Control mobile pushes | Suppress mobile pushes while actively at the terminal | v2.1.181 |
| `CLAUDE_CODE_DISABLE_NOTIFICATION_PRESENCE_CHECK` | Sends desktop notifications even while typing/focused (server can still suppress the mobile push) | Always get desktop notifications regardless of activity | v2.1.193 |
| `CLAUDE_CODE_USER_DIALOG_TIMEOUT_MS` | Deadline for dialogs forwarded to a remote client/SDK host and held cross-session messages (not permission prompts/`AskUserQuestion`); also bounds the Fable usage-credits consent prompt | Bound how long an unattended session waits on a remote dialog | — |
| `CLAUDE_CODE_MESSAGING_SOCKET` / `CLAUDE_CODE_MESSAGING_TOKEN` | Set by Claude Code (not settable via settings `env`): the session's inbox-socket path and per-session auth token, exported to hooks/Bash | Have a hook/script post messages to the session's own inbox | v2.1.224 / v2.1.228 |

## Terminal rendering, accessibility & UI

| Variable | What it does | Use cases | Date added |
|---|---|---|---|
| `CLAUDE_CODE_NO_FLICKER` | Enables fullscreen rendering (research preview, less flicker, flat memory); overridden by `CLAUDE_CODE_DISABLE_ALTERNATE_SCREEN` | Try the fullscreen renderer | — |
| `CLAUDE_CODE_DISABLE_ALTERNATE_SCREEN` | Forces the classic main-screen renderer, keeping native scrollback/`Cmd+f`/tmux copy mode; outranks `CLAUDE_CODE_NO_FLICKER` | Keep native terminal scrollback | — |
| `CLAUDE_CODE_ALT_SCREEN_FULL_REPAINT` | Repaints the whole screen every frame in fullscreen mode instead of incremental updates (auto-on for background sessions/agent view on Windows) | Fix stale/misplaced fragments in fullscreen mode | — |
| `CLAUDE_CODE_DISABLE_VIRTUAL_SCROLL` | Renders every transcript message instead of virtual-scrolling in fullscreen mode | Fix blank regions when scrolling | — |
| `CLAUDE_CODE_DISABLE_MOUSE` / `_DISABLE_MOUSE_CLICKS` | Disables all mouse tracking, or just clicks/drag/hover while keeping wheel scroll, in fullscreen mode | Preserve native terminal copy-on-select | `_DISABLE_MOUSE_CLICKS` v2.1.195 |
| `CLAUDE_CODE_SCROLL_SPEED` | Mouse-wheel scroll multiplier in fullscreen mode (up to 20, fractional allowed) | Slow down over-amplified trackpad/wheel scroll | — |
| `CLAUDE_CODE_FORCE_SYNC_OUTPUT` | Force-enables DEC 2026 synchronized output for undetected terminals | Fix flicker in an emulator that doesn't answer the capability probe | — |
| `CLAUDE_CODE_FORCE_STRIKETHROUGH` | Force-enables strikethrough rendering for undetected terminals (e.g. over SSH) | Fix literal `~~text~~` markers over SSH | v2.1.186 |
| `FORCE_HYPERLINK` | `1` forces OSC 8 hyperlinks on, `0` off; parsed as a number so `false`/`no` still enables | Force hyperlinks in an SSH session where the PR badge otherwise renders as plain text | — |
| `CLAUDE_CODE_NATIVE_CURSOR` | Shows the terminal's own cursor at the input caret instead of a drawn block | Respect terminal blink/shape/focus settings | — |
| `CLAUDE_CODE_ACCESSIBILITY` | Keeps the native terminal cursor visible, disables the inverted-text indicator | Let a screen magnifier track cursor position | — |
| `CLAUDE_AX_SCREEN_READER` | `1` renders flat screen-reader-friendly output; `0` force-disables it even if the setting is on | Screen-reader compatibility | v2.1.181 |
| `CLAUDE_AX_PREPARK_MS` / `CLAUDE_AX_STARTUP_QUIET_MS` | Delay before writing a changed line (default 50ms, capped 5000) / hold on first render after startup (default 3000ms, capped 10min) in screen-reader mode | Give a screen reader time to finish speaking | v2.1.233 / v2.1.217 |
| `CLAUDE_CODE_HIDE_CWD` | Hides the working directory in the startup logo | Avoid exposing a username/path on a screenshare | — |
| `CLAUDE_CODE_SYNTAX_HIGHLIGHT` | `false` disables diff syntax highlighting | Fix color conflicts with a terminal theme | — |
| `CLAUDE_CODE_TMUX_TRUECOLOR` | Allows 24-bit truecolor inside tmux; **`0`/`false` still allows it**, unset to restore the 256-color clamp | Get truecolor after configuring `terminal-overrides` in tmux | — |
| `CLAUDE_CODE_ENABLE_PROMPT_SUGGESTION` | `false` disables grayed-out prompt predictions; also auto-paused near usage limits | Turn off predictive prompt suggestions | v2.1.238 |
| `CLAUDE_AFK_COUNTDOWN_MS` | How many ms before auto-continue the on-screen countdown appears on an unanswered `AskUserQuestion` dialog (default 20000, capped at the auto-continue timeout below); has no effect unless auto-continue is on | Tune the visible countdown on an auto-continuing question dialog | v2.1.198 |
| `CLAUDE_AFK_TIMEOUT_MS` | How many ms of idle time before an unanswered `AskUserQuestion` dialog auto-continues without you; overrides the `askUserQuestionTimeout` setting and forces auto-continue on even when that setting is unset/`never`. `0` closes the dialog immediately rather than disabling the timeout | Demos/automated tests that must not block on an unattended question | v2.1.198 (default timeout was 60000 in v2.1.198–199) |
| `CLAUDE_CODE_ENABLE_AWAY_SUMMARY` | Force session recap on/off regardless of the `/config` toggle | Override recap availability | — |
| `CLAUDE_CODE_DISABLE_TERMINAL_TITLE` | Disables terminal-title auto-updates; also skips the background title-generation model call in SDK/`-p` mode | Avoid an extra small-model call in headless mode | — |
| `CLAUDE_CODE_AUTO_CONNECT_IDE` / `_IDE_HOST_OVERRIDE` / `_IDE_SKIP_AUTO_INSTALL` / `_IDE_SKIP_VALID_CHECK` | Control automatic IDE connection, connection host, extension auto-install, and lockfile validation | Fix IDE auto-connect in unusual setups (WSL, tmux, custom hosts) | — |
| `IS_DEMO` | Hides email/org name, skips onboarding; **`0`/`false` still enables it** | Streaming/recording a session | — |
| `DISABLE_COST_WARNINGS` | Disables cost-warning messages | Suppress cost nags in a cost-aware automated pipeline | — |

## Telemetry & OpenTelemetry

| Variable | What it does | Use cases | Date added |
|---|---|---|---|
| `CLAUDE_CODE_ENABLE_TELEMETRY` | Enables OTel metrics/logging (required before configuring exporters) | Turn telemetry collection on | — |
| `DISABLE_TELEMETRY` / `DO_NOT_TRACK` | Opt out of telemetry; also disables feature-flag fetching (same as `DISABLE_GROWTHBOOK`), which disables Remote Control and related features. **`0`/`false` still opts out** for `DISABLE_TELEMETRY`; `DO_NOT_TRACK` reads as a normal boolean | Org-wide telemetry opt-out | — |
| `DISABLE_GROWTHBOOK` | Disables GrowthBook feature-flag fetching specifically, same downstream effect as `DISABLE_TELEMETRY` on flag-gated features | Disable feature flags without disabling telemetry events | — |
| `CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC` | Disables auto-updates, telemetry, error reporting, `/feedback`, release notes, PR/MR badge checks, fast-mode availability check, and background plugin-command runs; also disables feature-flag fetching. **`0`/`false` still disables** | Airgapped/locked-down deployments | — |
| `CLAUDE_CODE_ENABLE_FEEDBACK_SURVEY_FOR_OTEL` | Routes the session-quality survey to your own OTel collector instead of Anthropic when nonessential traffic is blocked | Keep collecting survey signal under a telemetry opt-out | — |
| `CLAUDE_CODE_DISABLE_FEEDBACK_SURVEY` | Disables the "How is Claude doing?" survey outright (also off under the telemetry opt-outs unless the var above re-enables OTel routing) | Suppress the survey prompt | — |
| `OTEL_LOG_USER_PROMPTS` / `OTEL_LOG_ASSISTANT_RESPONSES` / `OTEL_LOG_TOOL_CONTENT` / `OTEL_LOG_TOOL_DETAILS` / `OTEL_LOG_RAW_API_BODIES` | Opt in to including prompt text, response text, tool content, tool metadata, or raw request/response bodies in OTel logs (all redacted/off by default for PII protection) | Deep telemetry debugging with PII risk accepted | `OTEL_LOG_ASSISTANT_RESPONSES` v2.1.193 |
| `CLAUDE_CODE_OTEL_CONTENT_MAX_LENGTH` | Max length of content-bearing OTel attributes (default 61440/60KB) | Fit within a telemetry backend's attribute-size limit | v2.1.214 |
| `OTEL_ATTRIBUTE_VALUE_LENGTH_LIMIT` (+ `OTEL_LOGRECORD_...`/`OTEL_SPAN_...` variants) | Standard OTel SDK attribute-length limit; the smallest of this and `CLAUDE_CODE_OTEL_CONTENT_MAX_LENGTH` wins | Coordinate with a generic OTel SDK size limit | v2.1.214 |
| `OTEL_METRICS_INCLUDE_ACCOUNT_UUID` / `_ENTRYPOINT` / `_RESOURCE_ATTRIBUTES` / `_SESSION_ID` / `_VERSION` | Include/exclude account UUID, entrypoint, resource attributes, session ID, or CLI version on metrics | Tune metric cardinality/PII exposure | `_ENTRYPOINT` v2.1.152, `_RESOURCE_ATTRIBUTES` behavior v2.1.161 |
| `CLAUDE_CODE_OTEL_FLUSH_TIMEOUT_MS` / `_SHUTDOWN_TIMEOUT_MS` | Timeout to flush pending spans (default 5000) / for the exporter to finish on shutdown (default 2000) | Avoid dropped telemetry at process exit | — |
| `CLAUDE_CODE_OTEL_DIAG_STDERR` | Writes OTel exporter diagnostic errors to stderr (normally only visible with `--debug`) | Surface a silently-failing exporter (e.g. port collision) | v2.1.179 |
| `CLAUDE_CODE_OTEL_HEADERS_HELPER_DEBOUNCE_MS` | Refresh interval for dynamic OTel headers (default 1740000/29min) | Tune dynamic-header refresh cadence | — |
| `BETA_TRACING_ENDPOINT` / `ENABLE_BETA_TRACING_DETAILED` | OTLP endpoint and enable-flag for detailed beta tracing (content-bearing span attributes, `claude_code.hook` span); ignored in project/local settings | Detailed tracing beta, shell/user/managed settings only | — |
| `CLAUDE_CODE_PROPAGATE_TRACEPARENT` | See Provider routing section | — | v2.1.152 |

## Artifacts, feedback & command visibility

| Variable | What it does | Use cases | Date added |
|---|---|---|---|
| `CLAUDE_CODE_DISABLE_ARTIFACT` | Turns off the Artifact tool permanently (no settings file can re-enable it); use `enableArtifact`/`disableArtifact` settings for a reversible toggle | Hard-disable web-page publishing | — |
| `CLAUDE_CODE_ARTIFACT_AUTO_OPEN` | `0` stops auto-opening the browser on new artifact publish | Suppress browser auto-open | — |
| `CLAUDE_CODE_ARTIFACT_COMMENTS` / `_ARTIFACT_COMMENTS_AUTOREACT` | `0` stops Claude reading/replying to artifact comments, or just auto-replying | Control artifact-comment interaction | v2.1.221 / v2.1.228 |
| `CLAUDE_CODE_SEND_FEEDBACK` | `0`/`1` toggles Claude-drafted feedback for a session (can't grant access itself; other off-switches still apply) | Per-session feedback-drafting toggle | — |
| `DISABLE_FEEDBACK_COMMAND` (alias `DISABLE_BUG_COMMAND`) | Disables `/feedback`, `/bug`, `/share` (all one path since v2.1.212) and Claude-drafted feedback | Remove feedback commands entirely | pre-v2.1.212 alias behavior |
| `DISABLE_DOCTOR_COMMAND` | Hides `/doctor`/`/checkup` skill (not the `claude doctor` terminal command) | Managed deployments without self-service diagnostics | pre-v2.1.205 scope differed |
| `DISABLE_LOGIN_COMMAND` / `DISABLE_LOGOUT_COMMAND` | Hides `/login` / `/logout` | External auth management | — |
| `DISABLE_INSTALL_GITHUB_APP_COMMAND` | Hides `/install-github-app` (already hidden on third-party providers) | Remove the GitHub-app install path | — |
| `DISABLE_EXTRA_USAGE_COMMAND` | Hides `/usage-credits` | Prevent self-service usage-credit purchases | — |
| `DISABLE_UPGRADE_COMMAND` | Hides `/upgrade` | Managed-plan deployments | — |
| `CLAUDE_CODE_DISABLE_FILE_CHECKPOINTING` | Disables file checkpointing (`/rewind` can't restore code) | Skip checkpoint overhead | — |
| `CLAUDE_CODE_DISABLE_CRON` | Disables scheduled tasks (`/loop`, cron tools); already-running scheduled tasks stop too | Remove the scheduling surface | — |
| `CLAUDE_CODE_DISABLE_ADVISOR_TOOL` | Disables the advisor tool/`/advisor` command; `advisorModel` ignored, `--advisor` becomes a no-op | Remove the second-opinion advisor feature | — |
| `CLAUDE_CODE_DISABLE_FAST_MODE` | Disables fast mode | Remove the fast-mode surface | — |
| `CLAUDE_CODE_SKIP_FAST_MODE_NETWORK_ERRORS` / `_SKIP_FAST_MODE_ORG_CHECK` | Treat a failed fast-mode availability check as available, or skip the client-side check (API still enforces org policy) | Work around a network/proxy that blocks the fast-mode check | — |
| `CLAUDE_CODE_ENABLE_OPUS_4_7_FAST_MODE` / `_OPUS_4_6_FAST_MODE_OVERRIDE` | **Removed/no-op**, superseded by the current fast-mode default | — | removed v2.1.142 / v2.1.160 |

## Debugging, installation & updates

| Variable | What it does | Use cases | Date added |
|---|---|---|---|
| `DEBUG` | Enables debug mode (`--debug` equivalent); only `1`/`true`/`yes`/`on` trigger it | Turn on debug logging | — |
| `CLAUDE_CODE_DEBUG_LOGS_DIR` | Overrides the debug log file path (a file, not a directory); needs `--debug`/`/debug`/`DEBUG` to actually log | Redirect debug logs | — |
| `CLAUDE_CODE_DEBUG_LOG_LEVEL` | Minimum level written to the debug log (`verbose`/`debug`/`info`/`warn`/`error`) | Tune debug-log verbosity | — |
| `DISABLE_ERROR_REPORTING` | Opts out of error reporting; **`0`/`false` still opts out** | Suppress error telemetry | — |
| `DISABLE_INSTALLATION_CHECKS` | Disables installation warnings | Manually-managed install locations | — |
| `DISABLE_AUTOUPDATER` | Disables background auto-updates (manual `claude update` still works) | Freeze the auto-update behavior | — |
| `DISABLE_UPDATES` | Blocks all updates including manual `claude update`/`claude install` | Fully vendor-controlled distribution | — |
| `CLAUDE_CODE_PACKAGE_MANAGER_AUTO_UPDATE` | Runs the package-manager upgrade command in the background (Homebrew/WinGet only) | Auto-upgrade via the OS package manager | — |
| `CCR_FORCE_BUNDLE` | Forces `claude --cloud` to bundle/upload the local repo even with GitHub access available | Force local-bundle upload for cloud sessions | — |

## Model-agnostic misc / SDK

| Variable | What it does | Use cases | Date added |
|---|---|---|---|
| `CLAUDE_CODE_EXTRA_BODY` | JSON merged into the top level of every API request body; a shell-exported value also applies to `claude agents`/`--bg` background sessions | Pass provider-specific request parameters | background-session inheritance fixed v2.1.206 |
| `CLAUDE_CODE_MAX_TURNS` | Caps agentic turns when no explicit limit is passed; `--max-turns` takes precedence | Bound a runaway automated session | — |
| `MAX_STRUCTURED_OUTPUT_RETRIES` | Retries when the model's response fails validation against `--json-schema` in non-interactive (`-p`) mode; same count applies to a workflow subagent's structured-output validation (default 5) | Tune retry budget for schema-constrained headless output | — |
