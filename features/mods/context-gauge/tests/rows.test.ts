import { describe, expect, test } from "claude-code/testing";

import { GAP_FLOOR_SHARE, GAP_FLOOR_TOKENS } from "../hooks/calibration";
import { PALETTES } from "../hooks/palette";
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

describe("gauge rows", () => {
	test("engine rows are named in bar order, empty rows left out, custom agents as agent descriptions", async () => {
		const rows = fixedOnly([
			{ name: "Skills", tokens: 900 },
			{ name: "System prompt", tokens: 3000 },
			{ name: "MCP tools", tokens: 0 },
			{ name: "Custom agents", tokens: 400 },
		]);

		expect(rows.map((r) => [r.id, r.label])).toEqual([
			["system", "system prompt & tools"],
			["agentList", "agent descriptions"],
			["skills", "skill list"],
		]);
	});

	test("the system prompt and the system tools make one system row", async () => {
		const rows = fixedOnly([
			{ name: "System prompt", tokens: 6000 },
			{ name: "System tools", tokens: 2000 },
		]);

		expect(rows.map((r) => [r.id, r.label, r.tokens])).toEqual([
			["system", "system prompt & tools", 8000],
		]);
	});

	test("the MCP tools and the MCP server instructions make one mcp row", async () => {
		const rows = fixedOnly([
			{ name: "MCP tools", tokens: 1500 },
			{ name: "Skills", tokens: 100 },
			{ name: "MCP server instructions", tokens: 500 },
		]);

		expect(rows.map((r) => [r.id, r.label, r.tokens])).toEqual([
			["mcp", "MCP servers", 2000],
			["skills", "skill list", 100],
		]);
	});

	test("a row the gauge does not know is shown lower-cased, after the rest", async () => {
		const rows = fixedOnly([
			{ name: "Workflow Scripts", tokens: 50 },
			{ name: "Memory files", tokens: 10 },
		]);

		expect(rows.map((r) => [r.id, r.label])).toEqual([
			["memory", "memory files"],
			["other", "workflow scripts"],
		]);
	});

	test("message categories draw their calibrated tokens beside the engine's fixed rows, in bar order, carried over right after skills", async () => {
		const rows = gaugeRows({
			fixed: [
				{ name: "Skills", tokens: 4000 },
				{ name: "System prompt", tokens: 6000 },
			],
			messages: { ...ZERO, read: 3000.4, messages: 1200, carried: 20_000 },
			gap: 0,
		});

		expect(rows.map((r) => [r.label, r.tokens, r.estimated])).toEqual([
			["system prompt & tools", 6000, false],
			["skill list", 4000, false],
			["carried over", 20_000, true],
			["messages", 1200, true],
			["file reads", 3000, true],
		]);
	});

	test(`the attribution gap draws only at or above ${GAP_FLOOR_TOKENS} tokens and ${GAP_FLOOR_SHARE * 100}% of message tokens`, async () => {
		const gapOf = (messages: number, gap: number) =>
			gaugeRows({ fixed: [], messages: { ...ZERO, messages }, gap }).find(
				(r) => r.id === "gap",
			);

		expect(gapOf(10_000, 1499)).toBeUndefined();
		expect(gapOf(10_000, 1500)?.label).toBe("attribution gap");
		// 2% of the 204,000 message tokens the gap is among is 4,080.
		expect(gapOf(200_000, 4000)).toBeUndefined();
		// 2% of 204,100 is 4,082.
		expect(gapOf(200_000, 4100)?.tokens).toBe(4100);
	});

	test("carried over is labelled 'carried over' and draws in the checker texture", async () => {
		const [carried] = gaugeRows({
			fixed: [],
			messages: { ...ZERO, carried: 5000 },
			gap: 0,
		});

		expect(carried?.label).toBe("carried over");
		expect(carried && PALETTES.dark[carried.id].texture).toBe("checker");
		expect(carried && PALETTES.light[carried.id].texture).toBe("checker");
	});
});
