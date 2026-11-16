import type {
	ContextCategory,
	ModelUsage,
	SessionContextBreakdown,
} from "claude-code";
import { describe, expect, test } from "claude-code/testing";
import { PRIOR_TOKENS_PER_CHAR } from "../hooks/calibration";
import { usageModel } from "../hooks/live";
import { windowAfter } from "../hooks/window";
import type { CompactionSetting, Ratio, Tally, Window } from "../types";

function row(
	name: string,
	tokens: number,
	kind: ContextCategory["kind"] = "used",
): ContextCategory {
	return { name, tokens, color: "inactive", isDeferred: false, kind };
}

function responseUsage(
	input: number,
	cacheRead: number,
	cacheCreation: number,
	output: number,
): ModelUsage {
	return {
		input_tokens: input,
		cache_read_input_tokens: cacheRead,
		cache_creation_input_tokens: cacheCreation,
		output_tokens: output,
	};
}

/** The breakdown's estimate of the window: 6,000 system prompt, 4,000 skills, 20,000 messages. */
const BREAKDOWN_TOTAL = 30_000;

function breakdown(
	rawMaxTokens: number,
	autoCompactThreshold?: number,
): SessionContextBreakdown {
	const b: SessionContextBreakdown = {
		categories: [
			row("System prompt", 6000),
			row("Skills", 4000),
			row("Messages", 20_000),
			row("Free space", rawMaxTokens - BREAKDOWN_TOTAL, "free"),
		],
		totalTokens: BREAKDOWN_TOTAL,
		maxTokens: rawMaxTokens,
		rawMaxTokens,
		autocompactSource: "model-default",
		percentage: Math.round((BREAKDOWN_TOTAL / rawMaxTokens) * 100),
		gridRows: [],
		model: "test",
		memoryFiles: [],
		mcpTools: [],
		agents: [],
		isAutoCompactEnabled: autoCompactThreshold !== undefined,
		apiUsage: null,
	};
	if (autoCompactThreshold !== undefined)
		b.autoCompactThreshold = autoCompactThreshold;
	return b;
}

const ZERO: Tally = {
	carried: 0,
	summary: 0,
	hooks: 0,
	plugins: 0,
	reminders: 0,
	files: 0,
	messages: 0,
	tasks: 0,
	relayed: 0,
	commands: 0,
	calls: 0,
	writes: 0,
	results: 0,
	read: 0,
	prompts: 0,
	agents: 0,
	thinking: 0,
};

/** The breakdown's fixed rows: 6,000 system prompt and 4,000 skills. */
const FIXED = 10_000;

/** No sample yet: the prior decides. */
const NO_RATIO: Ratio = { model: "", tokens: 0, chars: 0 };

/** A window a response measured at `messages` message tokens beside the fixed rows, with `keptChars` characters of messages kept since. */
function measured(messages: number, keptChars = 0): Window {
	return {
		cause: { family: "start", signal: "session.start" },
		measure: {
			kind: "measured",
			anchor: { window: FIXED + messages, fixed: FIXED, messageCount: 1 },
			tokens: { ...ZERO, messages },
			gap: 0,
		},
		open: { chars: { ...ZERO, messages: keptChars }, media: ZERO },
		tainted: false,
		inFlight: null,
		fingerprint: null,
		replaced: null,
	};
}

/** A window no response has measured yet: `carriedChars` of history read, and `keptChars` of messages kept since. */
function unmeasured(carriedChars: number, keptChars = 0): Window {
	return {
		cause: { family: "start", signal: "session.start" },
		measure: {
			kind: "unmeasured",
			history: { kind: "read", carriedChars, carriedMedia: 0 },
		},
		open: { chars: { ...ZERO, messages: keptChars }, media: ZERO },
		tainted: false,
		inFlight: null,
		fingerprint: null,
		replaced: null,
	};
}

/** A window a response measured at 20,000 message tokens, so used is the breakdown's 30,000. */
const MESSAGES_20K = measured(20_000);

/** Settings and environment that set nothing, leaving the engine's threshold to stand. */
const NO_SETTINGS: CompactionSetting = {
	enabled: true,
	window: null,
	percent: null,
};

/** The usage model of a session whose context carries breakdown `b`. */
function modelFor(
	b: SessionContextBreakdown,
	window: Window = MESSAGES_20K,
	compaction: CompactionSetting = NO_SETTINGS,
) {
	return usageModel(
		{ window: b.rawMaxTokens, breakdown: b },
		window,
		NO_RATIO,
		compaction,
	);
}

describe("the window after a response", () => {
	test("sums the input, both cache figures and the output", async () => {
		expect(windowAfter(responseUsage(10_000, 20_000, 500, 2000))).toBe(32_500);
	});
});

describe("the usage model", () => {
	test("before any response in a window, used is the fixed rows plus every estimate, and the totals read as estimated", async () => {
		const model = modelFor(breakdown(100_000), unmeasured(10_000, 2000));

		expect(model?.used).toBe(
			Math.round(FIXED + PRIOR_TOKENS_PER_CHAR * (10_000 + 2000)),
		);
		expect(model?.measured).toBe(false);
	});

	test("after a response, used is the window it measured plus what was kept since", async () => {
		const model = modelFor(breakdown(100_000), measured(22_000, 1000));

		expect(model?.used).toBe(
			Math.round(FIXED + 22_000 + PRIOR_TOKENS_PER_CHAR * 1000),
		);
		expect(model?.measured).toBe(true);
	});

	test("the fixed rows draw as the engine reports them, unscaled, without the Messages row", async () => {
		const model = modelFor(breakdown(100_000), measured(5000));

		expect(model?.fixed).toEqual([
			{ name: "System prompt", tokens: 6000 },
			{ name: "Skills", tokens: 4000 },
		]);
	});

	test("the breakdown's total and its Messages row never reach the used figure", async () => {
		const stale = breakdown(100_000);
		stale.totalTokens = 90_000;
		stale.categories = stale.categories.map((c) =>
			c.name === "Messages" ? { ...c, tokens: 80_000 } : c,
		);

		expect(modelFor(stale, unmeasured(0))?.used).toBe(FIXED);
	});

	test("the percentage divides used by the auto-compaction threshold, not the raw window", async () => {
		const model = modelFor(breakdown(100_000, 40_000));

		expect(model?.percent).toBe(75);
	});

	test("the percentage rounds to a whole number", async () => {
		expect(modelFor(breakdown(100_000, 80_000))?.percent).toBe(38);
	});

	test("the percentage stops at 100 past the ceiling", async () => {
		const model = modelFor(breakdown(100_000), measured(130_000));

		expect(model?.percent).toBe(100);
	});

	test("without a breakdown there is nothing to draw", async () => {
		expect(
			usageModel({ window: 100_000 }, MESSAGES_20K, NO_RATIO, NO_SETTINGS),
		).toBeNull();
	});

	test("a window of no tokens has nothing to draw", async () => {
		const empty = breakdown(100_000);
		empty.rawMaxTokens = 0;

		expect(modelFor(empty)).toBeNull();
	});
});
