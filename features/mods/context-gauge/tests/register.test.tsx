import { describe, expect, test } from 'claude-code/testing'
import type { Engine } from 'claude-code/testing'
import type { ContextCategory, On } from 'claude-code'

import { CATEGORY_SWATCHES, CHIP_TEXT, FILL_SWATCHES } from '../hooks/palette'

const HINT = {
  plugin: 'context-gauge',
  component: 'PromptHint',
  surface: 'terminal',
  props: { isDraft: false, isWorking: false, hint: '⏵⏵ accept edits on (shift+tab to cycle)' },
} as const

const ICONS = /[○◔◑◕●⊞⚙⇄◇▤✦✉]/

function row(name: string, tokens: number, kind: ContextCategory['kind'] = 'used'): ContextCategory {
  return { name, tokens, color: 'inactive', isDeferred: false, kind }
}

// Stands for the engine beneath the plugin: a session whose window holds
// 30,000 of 100,000 tokens, 20,000 of them messages.
function engine(on: On): void {
  on('session.start', (_, e) => ({ cwd: e.cwd }))
  on('env.get', () => ({ value: undefined }))
  on('classic.SessionStart', () => ({}))
  on('prompt.submit', (_, e) => ({ text: e.text }))
  on('session.usage', () => ({
    value: {
      startedAt: 0,
      rateLimits: [],
      context: {
        tokens: 30_000,
        window: 100_000,
        breakdown: {
          categories: [
            row('System prompt', 6000),
            row('Skills', 4000),
            row('Messages', 20_000),
            row('Free space', 70_000, 'free'),
          ],
          totalTokens: 30_000,
          maxTokens: 100_000,
          rawMaxTokens: 100_000,
          autocompactSource: 'model-default',
          percentage: 30,
          gridRows: [],
          model: 'test',
          memoryFiles: [],
          mcpTools: [],
          agents: [],
          isAutoCompactEnabled: false,
          apiUsage: null,
        },
      },
    },
  }))
  on('ui.render', ($, e) => {
    const { Text } = $.ui.resolve(e)
    return <Text>engine hint line</Text>
  })
}

const TYPED = { wait: false, origin: { kind: 'composer' } } as const

async function gaugeText($: Engine): Promise<string> {
  const ui = await $.ui.mount(HINT)
  const text = (await ui.find({ key: 'gauge' }))?.text ?? ''
  await ui.unmount()
  return text
}

describe('the gauge under the prompt', () => {
  test('sits on its own line beneath the engine hint line, percentage first, no icons', async ($, on) => {
    engine(on)
    await $.session.start({ cwd: '/', surface: 'terminal', isInteractive: true })

    const ui = await $.ui.mount(HINT)
    const texts = (await ui.findAll({ type: 'Text' })).map(t => t.text)
    const gauge = (await ui.find({ key: 'gauge' }))?.text ?? ''
    await ui.unmount()

    expect(texts[0]).toBe('engine hint line')
    expect(gauge.trimStart().startsWith('30%')).toBe(true)
    expect(ICONS.test(texts.join(''))).toBe(false)
  })

  test('each category word is a chip in its bar segment colour, black text on it', async ($, on) => {
    engine(on)
    await $.session.start({ cwd: '/', surface: 'terminal', isInteractive: true })

    const ui = await $.ui.mount(HINT)
    const chip = await ui.find({ type: 'Text', text: 'sys prompt' })
    const percent = await ui.find({ type: 'Text', text: '30%' })
    const segments = await ui.findAll({ type: 'Text', text: /▓/ })
    await ui.unmount()

    expect(chip?.props.backgroundColor).toBe(CATEGORY_SWATCHES.sysPrompt.hex)
    expect(chip?.props.color).toBe(CHIP_TEXT)
    expect(segments[0]?.props.color).toBe(CATEGORY_SWATCHES.sysPrompt.hex)
    expect(percent?.props.backgroundColor).toBe(FILL_SWATCHES.low.hex)
  })

  test('a submitted prompt shows as user text', async ($, on) => {
    engine(on)
    await $.session.start({ cwd: '/', surface: 'terminal', isInteractive: true })
    await $.prompt.submit({ ...TYPED, text: 'x'.repeat(4000) })

    expect(await gaugeText($)).toMatch(/user\s+~1k/)
  })

  test('a Read result shows as read text, unless a subagent made the call', async ($, on) => {
    engine(on)
    on('tool.call', () => ({
      result: {
        type: 'text',
        file: { filePath: '/a', content: 'x'.repeat(8000), numLines: 1, startLine: 1, totalLines: 1 },
      },
    }))
    await $.session.start({ cwd: '/', surface: 'terminal', isInteractive: true })
    await $.tool.call({ tool: 'Read', file_path: '/a' })
    await $.tool.call({ tool: 'Read', file_path: '/a', agentId: 'sub' })

    expect(await gaugeText($)).toMatch(/read\s+~2k/)
  })

  test('hook context shows as hooks text, unless it reached a subagent', async ($, on) => {
    engine(on)
    on('classic.UserPromptSubmit', () => ({ additionalContext: ['y'.repeat(12_000)] }))
    await $.session.start({ cwd: '/', surface: 'terminal', isInteractive: true })
    await $.classic.UserPromptSubmit({ prompt: 'hi' })
    await $.classic.UserPromptSubmit({ prompt: 'hi', agent_id: 'sub' })

    expect(await gaugeText($)).toMatch(/hooks\s+~3k/)
  })

  test('compaction clears the estimates', async ($, on) => {
    engine(on)
    await $.session.start({ cwd: '/', surface: 'terminal', isInteractive: true })
    await $.prompt.submit({ ...TYPED, text: 'x'.repeat(4000) })
    await $.classic.SessionStart({ source: 'compact' })

    expect(await gaugeText($)).not.toMatch(/user/)
  })
})
