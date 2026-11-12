/** The gauge's rows: the engine's breakdown rows named and ordered, its Messages row split by the gauge's estimates. */

import type { MessageEstimates, UsageCategory } from '../types'
import { CATEGORY_SWATCHES } from './palette'
import type { CategoryId } from './palette'

const CHARS_PER_TOKEN = 4

const ROW_IDS: Readonly<Record<string, Exclude<CategoryId, 'other'>>> = {
  'System prompt': 'sysPrompt',
  'System tools': 'sysTools',
  'MCP tools': 'mcpTools',
  'MCP server instructions': 'mcpInfo',
  'Custom agents': 'agents',
  'Memory files': 'memory',
  Skills: 'skills',
}

const LABELS: Readonly<Record<Exclude<CategoryId, 'other'>, string>> = {
  sysPrompt: 'sys prompt',
  sysTools: 'sys tools',
  mcpTools: 'mcp tools',
  mcpInfo: 'mcp info',
  agents: 'agents',
  memory: 'memory',
  skills: 'skills',
  hooks: 'hooks',
  user: 'user',
  read: 'read',
  replies: 'replies & tools',
}

const BAR_ORDER = Object.keys(CATEGORY_SWATCHES) as CategoryId[]

export type GaugeRow = { id: CategoryId; label: string; tokens: number; estimated: boolean }

function named(id: Exclude<CategoryId, 'other'>, tokens: number, estimated: boolean): GaugeRow {
  return { id, label: LABELS[id], tokens, estimated }
}

/** Splits the Messages row's tokens into estimated hook, user and Read rows and the remainder. */
function splitMessages(tokens: number, chars: MessageEstimates): GaugeRow[] {
  const seen = (chars.hooks + chars.user + chars.read) / CHARS_PER_TOKEN
  const scale = seen > tokens ? tokens / seen : 1
  const hooks = Math.round((chars.hooks / CHARS_PER_TOKEN) * scale)
  const user = Math.round((chars.user / CHARS_PER_TOKEN) * scale)
  const read = Math.round((chars.read / CHARS_PER_TOKEN) * scale)
  return [
    named('hooks', hooks, true),
    named('user', user, true),
    named('read', read, true),
    named('replies', Math.max(0, tokens - hooks - user - read), false),
  ]
}

/** The rows the gauge draws, in bar order, each with tokens. */
export function gaugeRows(categories: readonly UsageCategory[], chars: MessageEstimates): GaugeRow[] {
  const rows = categories.flatMap((c): GaugeRow[] => {
    if (c.name === 'Messages') return splitMessages(c.tokens, chars)
    const id = ROW_IDS[c.name]
    return [id ? named(id, c.tokens, false) : { id: 'other', label: c.name.toLowerCase(), tokens: c.tokens, estimated: false }]
  })
  return rows.filter(r => r.tokens > 0).sort((a, b) => BAR_ORDER.indexOf(a.id) - BAR_ORDER.indexOf(b.id))
}
