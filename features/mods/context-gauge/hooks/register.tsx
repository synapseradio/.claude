import { atom, read, update } from 'claude-code'
import type { EngineInterface, Register, SessionContextBreakdown } from 'claude-code'

import type { UsageModel } from '../types'

const usage = atom({ plugin: 'context-gauge', key: 'usage' } as const, null as UsageModel | null)

const BAR_CELLS = 14

/** Icon and short label for each breakdown row, keyed by the row name /context prints. */
const CATEGORY_TAGS: Readonly<Record<string, { icon: string; label: string }>> = {
  'System prompt': { icon: '⊞', label: 'sys' },
  'System tools': { icon: '⚙', label: 'tools' },
  'MCP tools': { icon: '⇄', label: 'mcp' },
  'MCP server instructions': { icon: '⇄', label: 'mcp info' },
  'Custom agents': { icon: '◇', label: 'agents' },
  'Memory files': { icon: '▤', label: 'memory' },
  Skills: { icon: '✦', label: 'skills' },
  Messages: { icon: '✉', label: 'msgs' },
}

function moon(percent: number): string {
  if (percent <= 0) return '○'
  if (percent < 25) return '◔'
  if (percent < 50) return '◑'
  if (percent < 75) return '◕'
  return '●'
}

function moonColor(percent: number): string {
  if (percent < 50) return 'success'
  if (percent < 80) return 'warning'
  return 'error'
}

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

function tagFor(name: string): string {
  const tag = CATEGORY_TAGS[name]
  return tag ? `${tag.icon} ${tag.label}` : name.toLowerCase()
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

async function modelFrom($: EngineInterface, b: SessionContextBreakdown | undefined): Promise<UsageModel | null> {
  if (!b || b.rawMaxTokens <= 0) return null
  const max = await effectiveMax($, b)
  const used = b.totalTokens
  const percent = Math.max(0, Math.min(100, Math.round((used / max) * 100)))
  const categories = b.categories
    .filter(c => c.kind === 'used' && c.tokens > 0)
    .map(c => ({ label: c.name, tokens: c.tokens, color: c.color, kind: c.kind }))
  return { used, max, percent, categories }
}

function barSegments(model: UsageModel): { color: string; chars: string }[] {
  const total = Math.max(model.max, 1)
  const parts = [
    ...model.categories.map(c => ({ tokens: c.tokens, char: '▓', color: c.color })),
    { tokens: Math.max(0, model.max - model.used), char: '░', color: 'inactive' },
  ]
  const raw = parts.map(p => (p.tokens / total) * BAR_CELLS)
  const cells = raw.map(r => Math.floor(r))
  let leftover = BAR_CELLS - cells.reduce((a, b) => a + b, 0)
  const order = raw
    .map((r, i) => i)
    .sort((a, b) => ((raw[b] ?? 0) % 1) - ((raw[a] ?? 0) % 1))
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
    const { context } = await $.session.usage({ breakdown: 'summary' })
    const model = await modelFrom($, context.breakdown)
    await update($, usage, () => model)
    return next(e)
  })

  on('session.measure', async ($, e, next) => {
    const { context } = await $.session.usage({ breakdown: 'summary' })
    const model = await modelFrom($, context.breakdown)
    await update($, usage, () => model)
    return next(e)
  })

  on('ui.render', { component: 'PromptHint' }, async ($, e, next) => {
    const model = await read($, usage)
    if (model === null) return next(e)

    const { Box, Text } = $.ui.resolve(e)
    const top = [...model.categories].sort((a, b) => b.tokens - a.tokens).slice(0, 2)

    return (
      <Box>
        <Text color={moonColor(model.percent)}>{moon(model.percent)}</Text>
        <Text> </Text>
        {barSegments(model).map((s, i) => (
          <Text key={`s${i}`} color={s.color}>
            {s.chars}
          </Text>
        ))}
        <Text> </Text>
        <Text>{model.percent}%</Text>
        <Text> </Text>
        <Text>
          {commas(model.used)}/{commas(model.max)}
        </Text>
        <Text> </Text>
        <Text dimColor>{phrase(model.percent)}</Text>
        {top.map((c, i) => (
          <Text key={`c${i}`} dimColor>
            {' '}· {tagFor(c.label)} {abbrev(c.tokens)}
          </Text>
        ))}
        {e.props.hint ? <Text dimColor> · {e.props.hint}</Text> : null}
      </Box>
    )
  })
}
