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

/** What settings files and environment variables decide about auto-compaction: whether it runs, the window it compacts at, and the share of that window that triggers it. */
export type CompactionSetting = {
	enabled: boolean;
	/** Tokens, or null where nothing sets a window and the engine's own threshold stands. */
	window: number | null;
	/** A percentage from 1 to 100, or null where none applies. */
	percent: number | null;
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
		"context-gauge": {
			/** The last breakdown read, or null before the first. */
			context: SessionContextUsage | null;
			/** What the settings files and environment decided about auto-compaction at the last read. */
			compaction: CompactionSetting;
			estimates: MessageEstimates;
			/** The window as the last main-thread response left it, or null before one. */
			anchor: number | null;
			/** Characters appended to the main conversation since the anchor. */
			pending: number;
			/** The glyphs the bar draws in where its Image draws its alt, or null while the Image draws. */
			glyphs: "sextant" | "bmp" | null;
		};
	}
}
