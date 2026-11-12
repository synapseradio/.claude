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

/** Characters the gauge has seen enter the window since it last cleared or compacted. */
export type MessageEstimates = {
	hooks: number;
	user: number;
	calls: number;
	results: number;
	read: number;
};

declare module "claude-code" {
	interface PluginState {
		"context-gauge": { usage: UsageModel | null; estimates: MessageEstimates };
	}
}
