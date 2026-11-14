import { describe, expect, test } from "claude-code/testing";

import { gaugeRows, NO_ESTIMATES } from "../hooks/rows";
import type { MessageEstimates } from "../types";

function estimates(chars: Partial<MessageEstimates>): MessageEstimates {
	return {
		summary: chars.summary ?? 0,
		hooks: chars.hooks ?? 0,
		plugins: chars.plugins ?? 0,
		reminders: chars.reminders ?? 0,
		files: chars.files ?? 0,
		messages: chars.messages ?? 0,
		scripts: chars.scripts ?? 0,
		commands: chars.commands ?? 0,
		calls: chars.calls ?? 0,
		writes: chars.writes ?? 0,
		results: chars.results ?? 0,
		read: chars.read ?? 0,
		prompts: chars.prompts ?? 0,
		agents: chars.agents ?? 0,
		thinking: chars.thinking ?? 0,
	};
}

describe("gauge rows", () => {
	test("engine rows are named in bar order, empty rows left out, custom agents as agent descriptions", async () => {
		const rows = gaugeRows(
			[
				{ name: "Skills", tokens: 900 },
				{ name: "System prompt", tokens: 3000 },
				{ name: "MCP tools", tokens: 0 },
				{ name: "Custom agents", tokens: 400 },
			],
			NO_ESTIMATES,
		);

		expect(rows.map((r) => [r.id, r.label])).toEqual([
			["system", "system prompt & tools"],
			["agentList", "agent descriptions"],
			["skills", "skill list"],
		]);
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
			["system", "system prompt & tools", 8000],
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
			["mcp", "MCP servers", 2000],
			["skills", "skill list", 100],
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
			["memory", "memory files"],
			["other", "workflow scripts"],
		]);
	});

	test("messages split into the counted categories at four characters a token, in bar order", async () => {
		const rows = gaugeRows([{ name: "Messages", tokens: 10_000 }], {
			summary: 2000,
			hooks: 6000,
			plugins: 400,
			reminders: 800,
			files: 1200,
			messages: 4000,
			scripts: 1200,
			commands: 800,
			calls: 1600,
			writes: 400,
			results: 6000,
			read: 12_000,
			prompts: 1600,
			agents: 2000,
			thinking: 0,
		});

		expect(rows.map((r) => [r.label, r.tokens, r.estimated])).toEqual([
			["compaction summary", 500, true],
			["hook output", 1500, true],
			["plugin context", 100, true],
			["Claude Code reminders", 200, true],
			["attached files", 300, true],
			["messages", 1000, true],
			["script results", 300, true],
			["slash commands", 200, true],
			["tool calls", 400, true],
			["file writes", 100, true],
			["tool results", 1500, true],
			["file reads", 3000, true],
			["agent prompts", 400, true],
			["agent reports", 500, true],
		]);
	});

	test("the remainder is the uncounted row, its label saying so", async () => {
		const rows = gaugeRows(
			[{ name: "Messages", tokens: 100 }],
			estimates({ messages: 40 }),
		);

		expect(rows.map((r) => [r.id, r.label])).toEqual([
			["messages", "messages"],
			["uncounted", "not yet counted"],
		]);
	});

	test("messages the estimates fall short of show as a not yet counted row of the difference", async () => {
		const rows = gaugeRows(
			[{ name: "Messages", tokens: 10_000 }],
			estimates({ messages: 4000, scripts: 8000 }),
		);

		expect(rows.map((r) => [r.label, r.tokens, r.estimated])).toEqual([
			["messages", 1000, true],
			["script results", 2000, true],
			["not yet counted", 7000, false],
		]);
	});

	test("estimates larger than the messages row shrink to fit it, leaving nothing uncounted", async () => {
		const rows = gaugeRows(
			[{ name: "Messages", tokens: 1000 }],
			estimates({ hooks: 4000, read: 2000, prompts: 2000 }),
		);

		expect(rows.map((r) => [r.label, r.tokens])).toEqual([
			["hook output", 500],
			["file reads", 250],
			["agent prompts", 250],
		]);
	});
});
