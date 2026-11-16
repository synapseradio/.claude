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
	plugins: number;
	reminders: number;
	files: number;
	messages: number;
	scripts: number;
	commands: number;
	calls: number;
	writes: number;
	results: number;
	read: number;
	prompts: number;
	agents: number;
	thinking: number;
};

export type CountedId =
	| "carried"
	| "summary"
	| "hooks"
	| "plugins"
	| "reminders"
	| "files"
	| "messages"
	| "tasks"
	| "relayed"
	| "commands"
	| "calls"
	| "writes"
	| "results"
	| "read"
	| "prompts"
	| "agents"
	| "thinking";

/** A number per message category. */
export type Tally = Readonly<Record<CountedId, number>>;

/** Kept rows before calibration: characters of text-like blocks, and token estimates of media blocks, by category. */
export type Pieces = { readonly chars: Tally; readonly media: Tally };

/** The signal that started a window, by its own name; one family's signals describe one transition. */
export type WindowCause =
	| {
			family: "start";
			signal: "session.start" | "classic.SessionStart:startup";
	  }
	| {
			family: "resume";
			signal:
				| "classic.SessionStart:resume"
				| "classic.SessionStart:fork"
				| "session.end:resume";
	  }
	| {
			family: "clear";
			signal:
				| "classic.SessionStart:clear"
				| "session.end:clear"
				| "session.append:plan_mode_exit"
				| "prompt.attachment:plan_mode_exit";
	  }
	| {
			family: "compaction";
			signal:
				| "session.append:compaction"
				| "session.compact"
				| "classic.SessionStart:compact";
	  }
	| { family: "unseen"; signal: "turn.step:messageCount" };

/** The conversation the engine held at the window's history read, less the rows this window kept before that read. */
export type History =
	| { kind: "unread"; why: "not-yet" | "failed" | "stale" | "truncated" }
	| { kind: "read"; carriedChars: number; carriedMedia: number };

/** One main response's exact figures. */
export type Anchor = { window: number; fixed: number; messageCount: number };

/** The request in flight: the input rows it carries, and its response's rows as they arrive. */
export type InFlight = {
	sent: Pieces;
	output: { visible: Pieces; thinking: boolean; served: Pieces };
	index: number;
	messageCount: number;
};

export type Measure =
	| { kind: "unmeasured"; history: History }
	| { kind: "measured"; anchor: Anchor; tokens: Tally; gap: number };

export type Window = {
	cause: WindowCause;
	measure: Measure;
	/** Input rows kept since the last request was built. */
	open: Pieces;
	/** A main row failed to count since the last request was built. */
	tainted: boolean;
	inFlight: InFlight | null;
	/** The window's first non-thinking assistant block, as a tool_use id or a hash; null before one. */
	fingerprint: string | null;
	/** The replaced window's fingerprint, so a history read that still returns that conversation is known stale. */
	replaced: string | null;
};

/** Pooled tokens per character of text-like pieces, per model. */
export type Ratio = { model: string; tokens: number; chars: number };

/** A history read: what the engine's conversation held, measured. */
export type HistoryRead = {
	chars: number;
	media: number;
	agentCalls: readonly string[];
	fingerprint: string | null;
	truncated: boolean;
};

/** A response's own blocks: visible text and calls, whether it held a thinking block, and server-run results it carried. */
export type OutputPieces = {
	visible: Pieces;
	thinking: boolean;
	served: Pieces;
};

/** What one kept row adds: input pieces, its output when it is a response's, and the Agent call ids it holds. */
export type RowPieces = {
	input: Pieces;
	output: OutputPieces | null;
	agentCalls: readonly string[];
};

declare module "claude-code" {
	interface PluginState {
		"context-gauge": {
			/** The last breakdown read, or null before the first. */
			context: SessionContextUsage | null;
			/** What the settings files and environment decided about auto-compaction at the last read. */
			compaction: CompactionSetting;
			estimates: MessageEstimates;
			/** The ids of the Agent calls the main conversation has kept, so a background agent's notification can be told apart from a script's; kept through /clear and compaction, since a notification may arrive after either. */
			agentCalls: readonly string[];
			/** The window as the last main-thread response left it, or null before one. */
			anchor: number | null;
			/** Characters appended to the main conversation since the anchor. */
			pending: number;
			/** The glyphs the bar draws in where its Image draws its alt, or null while the Image draws. */
			glyphs: "sextant" | "bmp" | null;
			/** The palette the gauge draws in. */
			theme: "light" | "dark";
		};
	}
}
