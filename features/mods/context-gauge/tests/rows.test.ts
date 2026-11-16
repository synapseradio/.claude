import { describe, expect, test } from "claude-code/testing";

import { GAP_FLOOR_SHARE, GAP_FLOOR_TOKENS } from "../hooks/calibration";
import type { GaugeRow } from "../hooks/rows";
import { gaugeRows } from "../hooks/rows";
import type { Tally, UsageCategory } from "../types";

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

/** The rows of a window holding only the engine's fixed rows. */
function fixedOnly(fixed: UsageCategory[]) {
	return gaugeRows({ fixed, messages: ZERO, gap: 0 });
}

function labels(rows: readonly GaugeRow[]): string[] {
	return rows.map((r) => r.label);
}

describe("the legend's rows", () => {
	test("the engine's rows are named in bar order, empty rows left out, custom agents as agent descriptions", async () => {
		const rows = fixedOnly([
			{ name: "Skills", tokens: 900 },
			{ name: "System prompt", tokens: 3000 },
			{ name: "MCP tools", tokens: 0 },
			{ name: "Custom agents", tokens: 400 },
		]);

		expect(labels(rows)).toEqual([
			"system prompt & tools",
			"agent descriptions",
			"skill list",
		]);
	});

	test("the system prompt and the system tools make one row", async () => {
		const rows = fixedOnly([
			{ name: "System prompt", tokens: 6000 },
			{ name: "System tools", tokens: 2000 },
		]);

		expect(rows.map((r) => [r.label, r.tokens])).toEqual([
			["system prompt & tools", 8000],
		]);
	});

	test("the MCP tools and the MCP server instructions make one row", async () => {
		const rows = fixedOnly([
			{ name: "MCP tools", tokens: 1500 },
			{ name: "Skills", tokens: 100 },
			{ name: "MCP server instructions", tokens: 500 },
		]);

		expect(rows.map((r) => [r.label, r.tokens])).toEqual([
			["MCP servers", 2000],
			["skill list", 100],
		]);
	});

	test("a row the gauge does not know is shown lower-cased, after the rest", async () => {
		const rows = fixedOnly([
			{ name: "Workflow Scripts", tokens: 50 },
			{ name: "Memory files", tokens: 10 },
		]);

		expect(labels(rows)).toEqual(["memory files", "workflow scripts"]);
	});

	test("message categories draw as estimates beside the engine's fixed rows, in bar order, carried over right after skills", async () => {
		const rows = gaugeRows({
			fixed: [
				{ name: "Skills", tokens: 4000 },
				{ name: "System prompt", tokens: 6000 },
			],
			messages: {
				...ZERO,
				read: 3000.4,
				messages: 1200,
				carried: 20_000,
				relayed: 500,
				tasks: 700,
			},
			gap: 0,
		});

		expect(rows.map((r) => [r.label, r.tokens, r.estimated])).toEqual([
			["system prompt & tools", 6000, false],
			["skill list", 4000, false],
			["carried over", 20_000, true],
			["messages", 1200, true],
			["background tasks", 700, true],
			["relayed messages", 500, true],
			["file reads", 3000, true],
		]);
	});

	test("the attribution gap shows only once it reaches both its token floor and its share of message tokens", async () => {
		const gapOf = (messages: number, gap: number) =>
			gaugeRows({ fixed: [], messages: { ...ZERO, messages }, gap }).find(
				(r) => r.label === "attribution gap",
			);
		// Message tokens large enough that the share, not the floor, decides;
		// the gap counts among the message tokens, so the share's boundary sits
		// where gap = share × (messages + gap).
		const many = (10 * GAP_FLOOR_TOKENS) / GAP_FLOOR_SHARE;
		const shareBoundary = (GAP_FLOOR_SHARE * many) / (1 - GAP_FLOOR_SHARE);

		expect(gapOf(0, GAP_FLOOR_TOKENS - 1)).toBeUndefined();
		expect(gapOf(0, GAP_FLOOR_TOKENS)?.tokens).toBe(GAP_FLOOR_TOKENS);
		expect(shareBoundary).toBeGreaterThan(GAP_FLOOR_TOKENS);
		expect(gapOf(many, Math.floor(shareBoundary) - 1)).toBeUndefined();
		expect(gapOf(many, Math.ceil(shareBoundary) + 1)).toBeDefined();
	});
});
