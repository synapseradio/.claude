import { atom, read, update } from 'claude-code'
import type { EngineInterface, Register, SessionContextBreakdown, SessionContextUsage } from 'claude-code'

import type { MessageEstimates, UsageModel } from '../types'
import { CATEGORY_SWATCHES, CHIP_TEXT, fillSwatch } from './palette'
import { gaugeRows } from './rows'
import type { GaugeRow } from './rows'

const usage = atom({ plugin: 'context-gauge', key: 'usage' } as const, null as UsageModel | null)

const NO_ESTIMATES: MessageEstimates = { hooks: 0, user: 0, read: 0 }
const estimates = atom({ plugin: 'context-gauge', key: 'estimates' } as const, NO_ESTIMATES)

const BAR_CELLS = 14

function phrase(percent: number): string {
  if (percent <= 0) return 'fresh canvas'
  if (percent < 20) return 'roomy'
  if (percent < 40) return 'comfy'
  if (percent < 60) return 'getting snug'
  if (percent < 75) return 'cozy in here'
  if (percent < 90) return 'toasty'
  return 'about to compact'
}

function abbrev(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1).replace(/\.0$/, '')}M`
  if (n >= 10_000) return `${Math.round(n / 1000)}k`
  if (n >= 1000) return `${(n / 1000).toFixed(1).replace(/\.0$/, '')}k`
  return String(n)
}

function commas(n: number): string {
  return String(n).replace(/\B(?=(\d{3})+(?!\d))/g, ',')
}

async function effectiveMax($: EngineInterface, b: SessionContextBreakdown): Promise<number> {
  // The breakdown's `autoCompactThreshold` ignores CLAUDE_AUTOCOMPACT_PCT_OVERRIDE,
  // so derive the ceiling from the override the way the settings file states it.
  const pctRaw = await $.env.get('CLAUDE_AUTOCOMPACT_PCT_OVERRIDE')
  const pct = pctRaw ? Number(pctRaw) : NaN
  if (Number.isFinite(pct) && pct > 0 && pct <= 100) {
    return Math.floor((b.rawMaxTokens * pct) / 100)
  }
  return b.autoCompactThreshold ?? b.rawMaxTokens
}

/**
 * Counts `used` from the last API response's input tokens, the figure the
 * status line shows, and falls back to the breakdown's local estimate until a
 * response arrives in a fresh, cleared, or compacted window. Category figures
 * are scaled so they sum to `used`.
 */
async function modelFrom($: EngineInterface, context: SessionContextUsage): Promise<UsageModel | null> {
  const b = context.breakdown
  if (!b || b.rawMaxTokens <= 0) return null
  const max = await effectiveMax($, b)
  const used = context.tokens ?? b.totalTokens
  const percent = Math.max(0, Math.min(100, Math.round((used / max) * 100)))
  const scale = b.totalTokens > 0 ? used / b.totalTokens : 1
  const categories = b.categories
    .filter(c => c.kind === 'used' && c.tokens > 0)
    .map(c => ({ name: c.name, tokens: Math.round(c.tokens * scale) }))
  return { used, max, percent, categories }
}

async function refresh($: EngineInterface): Promise<void> {
  const { context } = await $.session.usage({ breakdown: 'summary' })
  const model = await modelFrom($, context)
  await update($, usage, () => model)
}

async function count($: EngineInterface, field: keyof MessageEstimates, chars: number): Promise<void> {
  if (chars > 0) await update($, estimates, e => ({ ...e, [field]: e[field] + chars }))
}

/** Characters a classic hook result hands the model: its context entries and its block reason. */
function hookChars(result: { additionalContext?: readonly string[]; block?: string }): number {
  const context = (result.additionalContext ?? []).reduce((sum, text) => sum + text.length, 0)
  return context + (result.block?.length ?? 0)
}

/** Counts a main-thread hook result; a subagent's hooks fill the subagent's window. */
async function countHooks<R extends { additionalContext?: readonly string[]; block?: string }>(
  $: EngineInterface,
  fromSubagent: boolean,
  result: R,
): Promise<R> {
  if (!fromSubagent) await count($, 'hooks', hookChars(result))
  return result
}

function barSegments(model: UsageModel, rows: readonly GaugeRow[]): { color: string; chars: string }[] {
  const total = Math.max(model.max, 1)
  const parts = [
    ...rows.map(r => ({ tokens: r.tokens, char: '▓', color: CATEGORY_SWATCHES[r.id].hex })),
    { tokens: Math.max(0, model.max - model.used), char: '░', color: 'inactive' },
  ]
  const raw = parts.map(p => (p.tokens / total) * BAR_CELLS)
  const cells = raw.map(r => Math.floor(r))
  const leftover = BAR_CELLS - cells.reduce((a, b) => a + b, 0)
  const order = raw.map((_, i) => i).sort((a, b) => ((raw[b] ?? 0) % 1) - ((raw[a] ?? 0) % 1))
  for (let k = 0; k < leftover; k++) {
    const i = order[k % order.length]
    if (i !== undefined) cells[i] = (cells[i] ?? 0) + 1
  }

  const out: { color: string; chars: string }[] = []
  for (let i = 0; i < parts.length; i++) {
    const cell = cells[i] ?? 0
    const part = parts[i]
    if (cell > 0 && part) out.push({ color: part.color, chars: part.char.repeat(cell) })
  }
  return out
}

export const register: Register = on => {
  on('session.start', async ($, e, next) => {
    await refresh($)
    return next(e)
  })

  on('session.measure', async ($, e, next) => {
    await refresh($)
    return next(e)
  })

  // `/clear` ends the session without a `session.start` for the new one, and
  // compaction replaces the messages the estimates counted; the classic
  // SessionStart event carries both as its `source`.
  on('classic.SessionStart', async ($, e, next) => {
    if (e.source === 'clear' || e.source === 'compact') await update($, estimates, () => NO_ESTIMATES)
    const result = await next(e)
    await count($, 'hooks', hookChars(result))
    await refresh($)
    return result
  }).catch(($, e, next) => next(e))

  // Only a person's own typing counts as user text: task notifications, peers
  // and scheduled triggers enter the window too, and stay in `replies & tools`.
  on('prompt.submit', async ($, e, next) => {
    const result = await next(e)
    const typed = e.origin.kind === 'composer' || e.origin.kind === 'bridge'
    if (typed && !e.isMeta && result.drop === undefined) await count($, 'user', e.text.length)
    return result
  }).catch(($, e, next) => next(e))

  on('tool.call', { tool: 'Read' }, async ($, e, next) => {
    const result = await next(e)
    const output = 'result' in result && !result.isError ? result.result : undefined
    if (e.agentId === undefined && output?.type === 'text') await count($, 'read', output.file.content.length)
    return result
  }).catch(($, e, next) => next(e))

  on('classic.Setup', async ($, e, next) => countHooks($, e.agent_id !== undefined, await next(e))).catch(($, e, next) => next(e))
  on('classic.UserPromptSubmit', async ($, e, next) => countHooks($, e.agent_id !== undefined, await next(e))).catch(($, e, next) => next(e))
  on('classic.UserPromptExpansion', async ($, e, next) => countHooks($, e.agent_id !== undefined, await next(e))).catch(($, e, next) => next(e))
  on('classic.PostToolUse', async ($, e, next) => countHooks($, e.agent_id !== undefined, await next(e))).catch(($, e, next) => next(e))
  on('classic.PostToolUseFailure', async ($, e, next) => countHooks($, e.agent_id !== undefined, await next(e))).catch(($, e, next) => next(e))
  on('classic.PostToolBatch', async ($, e, next) => countHooks($, e.agent_id !== undefined, await next(e))).catch(($, e, next) => next(e))
  on('classic.Stop', async ($, e, next) => countHooks($, e.agent_id !== undefined, await next(e))).catch(($, e, next) => next(e))
  on('classic.PostModelSwitch', async ($, e, next) => countHooks($, e.agent_id !== undefined, await next(e))).catch(($, e, next) => next(e))

  on('ui.render', { component: 'PromptHint' }, async ($, e, next) => {
    const model = await read($, usage)
    if (model === null) return next(e)

    const { Box, Text } = $.ui.resolve(e)
    const rows = gaugeRows(model.categories, await read($, estimates))

    return (
      <Box flexDirection="column">
        {await next(e)}
        <Box key="gauge">
          <Text color={CHIP_TEXT} backgroundColor={fillSwatch(model.percent).hex}>
            {` ${model.percent}% `}
          </Text>
          <Text> </Text>
          {barSegments(model, rows).map((s, i) => (
            <Text key={`s${i}`} color={s.color}>
              {s.chars}
            </Text>
          ))}
          <Text>
            {' '}
            {commas(model.used)}/{commas(model.max)}{' '}
          </Text>
          <Text dimColor>{phrase(model.percent)}</Text>
          {rows.map(r => (
            <Box key={`row-${r.id}-${r.label}`}>
              <Text dimColor> · </Text>
              <Text color={CHIP_TEXT} backgroundColor={CATEGORY_SWATCHES[r.id].hex}>
                {` ${r.label} `}
              </Text>
              <Text> {`${r.estimated ? '~' : ''}${abbrev(r.tokens)}`}</Text>
            </Box>
          ))}
        </Box>
      </Box>
    )
  })
}
