import { describe, expect, test } from "claude-code/testing";

import { gaugeRows, NO_ESTIMATES } from "../hooks/rows";

describe("gauge rows", () => {
	test("engine rows are named in bar order, empty rows left out", async () => {
		const rows = gaugeRows(
			[
				{ name: "Skills", tokens: 900 },
				{ name: "System prompt", tokens: 3000 },
				{ name: "MCP tools", tokens: 0 },
				{ name: "Custom agents", tokens: 400 },
			],
			NO_ESTIMATES,
		);

		expect(rows.map((r) => r.label)).toEqual(["system", "agents", "skills"]);
	});

	test("the system prompt and the system tools make one system row", async () => {
		const rows = gaugeRows(
			[
				{ name: "System prompt", tokens: 6000 },
				{ name: "System tools", tokens: 2000 },
			],
			NO_ESTIMATES,
		);

		expect(rows.map((r) => [r.id, r.label, r.tokens])).toEqual([
			["system", "system", 8000],
		]);
	});

	test("the MCP tools and the MCP server instructions make one mcp row", async () => {
		const rows = gaugeRows(
			[
				{ name: "MCP tools", tokens: 1500 },
				{ name: "Skills", tokens: 100 },
				{ name: "MCP server instructions", tokens: 500 },
			],
			NO_ESTIMATES,
		);

		expect(rows.map((r) => [r.id, r.label, r.tokens])).toEqual([
			["mcp", "mcp", 2000],
			["skills", "skills", 100],
		]);
	});

	test("a row the gauge does not know is shown lower-cased, after the rest", async () => {
		const rows = gaugeRows(
			[
				{ name: "Workflow Scripts", tokens: 50 },
				{ name: "Memory files", tokens: 10 },
			],
			NO_ESTIMATES,
		);

		expect(rows.map((r) => [r.id, r.label])).toEqual([
			["memory", "memory"],
			["other", "workflow scripts"],
		]);
	});

	test("messages split into hook text, user prompts, tool calls, tool results and Read results at four characters a token", async () => {
		const rows = gaugeRows([{ name: "Messages", tokens: 10_000 }], {
			hooks: 8000,
			user: 4000,
			calls: 2000,
			results: 6000,
			read: 12_000,
		});

		expect(rows.map((r) => [r.label, r.tokens, r.estimated])).toEqual([
			["hooks", 2000, true],
			["user", 1000, true],
			["calls", 500, true],
			["results", 1500, true],
			["read", 3000, true],
			["replies", 2000, false],
		]);
	});

	test("estimates larger than the messages row shrink to fit it", async () => {
		const rows = gaugeRows([{ name: "Messages", tokens: 1000 }], {
			hooks: 4000,
			user: 0,
			calls: 0,
			results: 0,
			read: 4000,
		});

		expect(rows.map((r) => [r.label, r.tokens])).toEqual([
			["hooks", 500],
			["read", 500],
		]);
	});
});
