/** One breakdown row as the engine names it, its tokens scaled to the window's measured use. */
export type UsageCategory = {
	name: string;
	tokens: number;
};

export type UsageModel = {
	used: number;
	max: number;
	percent: number;
	categories: UsageCategory[];
};

/** Characters the gauge has counted into each message category since the window last cleared or compacted. */
export type MessageEstimates = {
	summary: number;
	hooks: number;
	attachments: number;
	user: number;
	commands: number;
	deliveries: number;
	calls: number;
	results: number;
	read: number;
	thinking: number;
	replies: number;
};

declare module "claude-code" {
	interface PluginState {
		"context-gauge": { usage: UsageModel | null; estimates: MessageEstimates };
	}
}
