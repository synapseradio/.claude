import type {
	ContextCategory,
	ModelUsage,
	SessionContextBreakdown,
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

/** A response's usage that generated `output` tokens and read nothing. */
function turnUsage(output: number): TurnUsage {
	return Object.assign(responseUsage(0, 0, 0, output), { model: "test" });
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

const NO_ANCHOR = { anchor: null, pending: 0 };

/** The usage model of a session whose context carries breakdown `b`. */
function modelFor(
	b: SessionContextBreakdown,
	live: Parameters<typeof usageModel>[1] = NO_ANCHOR,
) {
	return usageModel({ window: b.rawMaxTokens, breakdown: b }, live);
}

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

		expect(thinkingTokens(step)).toBe(979);
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
		expect(modelFor(breakdown(100_000))?.used).toBe(30_000);
	});

	test("an anchored response plus 4,000 pending characters reads 33,000 used", async () => {
		const anchor = windowAfter(responseUsage(10_000, 20_000, 0, 2000));
		const model = modelFor(breakdown(100_000), { anchor, pending: 4000 });

		expect(model?.used).toBe(33_000);
	});

	test("an anchor of 5,000 from a compaction with nothing pending reads 5,000 used", async () => {
		const model = modelFor(breakdown(100_000), { anchor: 5000, pending: 0 });

		expect(model?.used).toBe(5000);
	});

	test("categories scale to used and keep only used rows", async () => {
		const model = modelFor(breakdown(100_000), { anchor: 15_000, pending: 0 });

		expect(model?.categories).toEqual([
			{ name: "System prompt", tokens: 3000 },
			{ name: "Skills", tokens: 2000 },
			{ name: "Messages", tokens: 10_000 },
		]);
	});

	test("a breakdown totalling 0 leaves categories unscaled", async () => {
		const b = breakdown(100_000);
		b.totalTokens = 0;
		const model = modelFor(b, { anchor: 5000, pending: 0 });

		expect(model?.categories.map((c) => c.tokens)).toEqual([
			6000, 4000, 20_000,
		]);
	});

	test("the ceiling is the auto-compaction threshold", async () => {
		expect(modelFor(breakdown(100_000, 80_000))?.max).toBe(80_000);
	});

	test("with auto-compaction off, the ceiling is the raw window", async () => {
		expect(modelFor(breakdown(100_000))?.max).toBe(100_000);
	});

	test("the percentage divides used by the auto-compaction threshold, not the raw window", async () => {
		const model = modelFor(breakdown(100_000, 40_000));

		expect(model?.percent).toBe(75);
	});

	test("the percentage rounds to a whole number", async () => {
		expect(modelFor(breakdown(100_000, 80_000))?.percent).toBe(38);
	});

	test("the percentage stops at 100 past the ceiling", async () => {
		const model = modelFor(breakdown(100_000), {
			anchor: 140_000,
			pending: 0,
		});

		expect(model?.percent).toBe(100);
	});

	test("no breakdown gives no model", async () => {
		expect(usageModel({ window: 100_000 }, NO_ANCHOR)).toBeNull();
	});

	test("an empty window gives no model", async () => {
		const empty = breakdown(100_000);
		empty.rawMaxTokens = 0;

		expect(modelFor(empty)).toBeNull();
	});
});
