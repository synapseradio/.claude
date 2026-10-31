export type UsageCategory = {
  label: string
  tokens: number
  color: string
  kind: string
}

export type UsageModel = {
  used: number
  max: number
  percent: number
  categories: UsageCategory[]
}

declare module 'claude-code' {
  interface PluginState {
    'context-gauge': { usage: UsageModel | null }
  }
}
