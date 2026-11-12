import { describe, expect, test } from "claude-code/testing";

import { gaugeRows, NO_ESTIMATES } from "../hooks/rows";
import type { MessageEstimates } from "../types";

function estimates(chars: Partial<MessageEstimates>): MessageEstimates {
	return {
		summary: chars.summary ?? 0,
		hooks: chars.hooks ?? 0,
		attachments: chars.attachments ?? 0,
		user: chars.user ?? 0,
		commands: chars.commands ?? 0,
		deliveries: chars.deliveries ?? 0,
		calls: chars.calls ?? 0,
		results: chars.results ?? 0,
		read: chars.read ?? 0,
		thinking: chars.thinking ?? 0,
		replies: chars.replies ?? 0,
	};
}

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

	test("messages split into the counted categories at four characters a token, in bar order", async () => {
		const rows = gaugeRows([{ name: "Messages", tokens: 10_000 }], {
			summary: 2000,
			hooks: 8000,
			attachments: 400,
			user: 4000,
			commands: 800,
			deliveries: 1200,
			calls: 2000,
			results: 6000,
			read: 12_000,
			thinking: 0,
			replies: 1600,
		});

		expect(rows.map((r) => [r.label, r.tokens, r.estimated])).toEqual([
			["summary", 500, true],
			["hooks", 2000, true],
			["attachments", 100, true],
			["user", 1000, true],
			["commands", 200, true],
			["deliveries", 300, true],
			["calls", 500, true],
			["results", 1500, true],
			["read", 3000, true],
			["replies", 400, true],
			["unattributed", 500, false],
		]);
	});

	test("messages the estimates fall short of show as an unattributed row of the difference", async () => {
		const rows = gaugeRows(
			[{ name: "Messages", tokens: 10_000 }],
			estimates({ user: 4000, replies: 8000 }),
		);

		expect(rows.map((r) => [r.label, r.tokens, r.estimated])).toEqual([
			["user", 1000, true],
			["replies", 2000, true],
			["unattributed", 7000, false],
		]);
	});

	test("estimates larger than the messages row shrink to fit it, leaving nothing unattributed", async () => {
		const rows = gaugeRows(
			[{ name: "Messages", tokens: 1000 }],
			estimates({ hooks: 4000, read: 2000, replies: 2000 }),
		);

		expect(rows.map((r) => [r.label, r.tokens])).toEqual([
			["hooks", 500],
			["read", 250],
			["replies", 250],
		]);
	});
});
