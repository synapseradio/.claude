import type {
	ContextCategory,
	ModelUsage,
	SessionContextBreakdown,
	SessionContextUsage,
	TurnUsage,
} from "claude-code";
import { describe, expect, test } from "claude-code/testing";

import { thinkingTokens, usageModel, windowAfter } from "../hooks/live";

function row(
	name: string,
	tokens: number,
	kind: ContextCategory["kind"] = "used",
): ContextCategory {
	return { name, tokens, color: "inactive", isDeferred: false, kind };
}

/** A response's usage: `input` uncached, `cacheRead` and `cacheCreation` from the prompt cache, `output` generated. */
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

/**
 * A window of `rawMaxTokens` holding the breakdown's estimate of 30,000
 * tokens: 6,000 system prompt, 4,000 skills, 20,000 messages.
 */
function breakdown(
	rawMaxTokens: number,
	autoCompactThreshold?: number,
): SessionContextBreakdown {
	const b: SessionContextBreakdown = {
		categories: [
			row("System prompt", 6000),
			row("Skills", 4000),
			row("Messages", 20_000),
			row("Free space", rawMaxTokens - 30_000, "free"),
		],
		totalTokens: 30_000,
		maxTokens: rawMaxTokens,
		rawMaxTokens,
		autocompactSource: "model-default",
		percentage: Math.round((30_000 / rawMaxTokens) * 100),
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

function context(b: SessionContextBreakdown): SessionContextUsage {
	return { window: b.rawMaxTokens, breakdown: b };
}

/** A response's usage that generated `output` tokens and read nothing. */
function turnUsage(output: number): TurnUsage {
	return {
		input_tokens: 0,
		cache_read_input_tokens: 0,
		cache_creation_input_tokens: 0,
		output_tokens: output,
		model: "test",
	};
}

const NO_ANCHOR = { anchor: null, pending: 0 };

describe("the window after a response", () => {
	test("sums the input, both cache figures and the output", async () => {
		expect(windowAfter(responseUsage(10_000, 20_000, 500, 2000))).toBe(32_500);
	});
});

describe("thinking tokens", () => {
	test("output tokens less a 400-character answer leave 2,900 thinking tokens", async () => {
		const step = {
			answer: "a".repeat(400),
			toolUses: [],
			usage: turnUsage(3000),
		};

		expect(thinkingTokens(step)).toBe(2900);
	});

	test("tool calls count as visible output, at their JSON length", async () => {
		// {"name":"Read","input":{"file_path":"/a"}} is 42 characters.
		const toolUse = { name: "Read", input: { file_path: "/a" } };
		const step = {
			answer: "",
			toolUses: [toolUse, toolUse],
			usage: turnUsage(1000),
		};

		expect(thinkingTokens(step)).toBe(1000 - (2 * 42) / 4);
	});

	test("an answer longer than the output tokens cover leaves 0 thinking tokens", async () => {
		const step = {
			answer: "a".repeat(4000),
			toolUses: [],
			usage: turnUsage(100),
		};

		expect(thinkingTokens(step)).toBe(0);
	});

	test("a step without usage spent no thinking tokens", async () => {
		expect(thinkingTokens({ answer: "", toolUses: [], usage: null })).toBe(0);
	});
});

describe("the usage model", () => {
	test("before any anchor, used is the breakdown's total", async () => {
		const model = usageModel(context(breakdown(100_000)), NO_ANCHOR, undefined);

		expect(model?.used).toBe(30_000);
		expect(model?.percent).toBe(30);
	});

	test("an anchored response plus 4,000 pending characters reads 33,000 used", async () => {
		const anchor = windowAfter(responseUsage(10_000, 20_000, 0, 2000));
		const model = usageModel(
			context(breakdown(100_000)),
			{ anchor, pending: 4000 },
			undefined,
		);

		expect(model?.used).toBe(33_000);
	});

	test("an anchor of 5,000 from a compaction with nothing pending reads 5,000 used", async () => {
		const model = usageModel(
			context(breakdown(100_000)),
			{ anchor: 5000, pending: 0 },
			undefined,
		);

		expect(model?.used).toBe(5000);
		expect(model?.percent).toBe(5);
	});

	test("categories scale to used and keep only used rows", async () => {
		const model = usageModel(
			context(breakdown(100_000)),
			{ anchor: 15_000, pending: 0 },
			undefined,
		);

		expect(model?.categories).toEqual([
			{ name: "System prompt", tokens: 3000 },
			{ name: "Skills", tokens: 2000 },
			{ name: "Messages", tokens: 10_000 },
		]);
	});

	test("a breakdown totalling 0 leaves categories unscaled", async () => {
		const b = breakdown(100_000);
		b.totalTokens = 0;
		const model = usageModel(
			context(b),
			{ anchor: 5000, pending: 0 },
			undefined,
		);

		expect(model?.categories.map((c) => c.tokens)).toEqual([
			6000, 4000, 20_000,
		]);
	});

	test("the ceiling is the auto-compaction threshold where no override is set", async () => {
		const model = usageModel(
			context(breakdown(100_000, 80_000)),
			NO_ANCHOR,
			undefined,
		);

		expect(model?.max).toBe(80_000);
		expect(model?.percent).toBe(38);
	});

	test("CLAUDE_AUTOCOMPACT_PCT_OVERRIDE sets the ceiling as a share of the raw window", async () => {
		const model = usageModel(
			context(breakdown(100_000, 80_000)),
			NO_ANCHOR,
			"50",
		);

		expect(model?.max).toBe(50_000);
		expect(model?.percent).toBe(60);
	});

	test("an override outside 1 to 100 leaves the breakdown's ceiling", async () => {
		const b = breakdown(100_000, 80_000);

		expect(usageModel(context(b), NO_ANCHOR, "0")?.max).toBe(80_000);
		expect(usageModel(context(b), NO_ANCHOR, "150")?.max).toBe(80_000);
		expect(usageModel(context(b), NO_ANCHOR, "half")?.max).toBe(80_000);
	});

	test("the percentage stops at 100 past the ceiling", async () => {
		const model = usageModel(
			context(breakdown(100_000)),
			{ anchor: 140_000, pending: 0 },
			undefined,
		);

		expect(model?.percent).toBe(100);
	});

	test("no breakdown, or an empty window, gives no model", async () => {
		expect(usageModel({ window: 100_000 }, NO_ANCHOR, undefined)).toBeNull();
		const empty = breakdown(100_000);
		empty.rawMaxTokens = 0;
		expect(usageModel(context(empty), NO_ANCHOR, undefined)).toBeNull();
	});
});
