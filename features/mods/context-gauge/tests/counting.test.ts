import type { ApiContentBlock, SessionAppendInput } from "claude-code";
import { describe, expect, test } from "claude-code/testing";

import { addCounts, rowEffect, rowPieces } from "../hooks/counting";
import { NO_ESTIMATES } from "../hooks/rows";
import { AGENT_CALL, agentUse, BASH_CALL, notification } from "./calls";

type Row = Pick<SessionAppendInput, "door" | "origin" | "message">;

function userRow(
	door: Row["door"],
	origin: Row["origin"],
	content: ApiContentBlock[],
): Row {
	return { door, origin, message: { type: "user", role: "user", content } };
}

function attachmentRow(
	door: Row["door"],
	origin: Row["origin"],
	content: ApiContentBlock[],
	name = "x",
): Row {
	return {
		door,
		origin,
		message: { type: "attachment", name, role: "user", content },
	};
}

function responseRow(...blocks: ApiContentBlock[]): Row {
	return {
		door: "response",
		origin: { kind: "model", model: "test" },
		message: { type: "assistant", role: "assistant", content: blocks },
	};
}

function text(chars: number): ApiContentBlock {
	return { type: "text", text: "x".repeat(chars) };
}

const READ: Row["origin"] = { kind: "tool", tool: "Read" };
const BASH: Row["origin"] = { kind: "tool", tool: "Bash" };
const AGENT: Row["origin"] = { kind: "tool", tool: "Agent" };
const NOTIFICATION: Row["origin"] = { kind: "task-notification" };

/** Nothing kept: no Agent call seen yet. */
const NO_CALLS: ReadonlySet<string> = new Set();

describe("what one appended row counts", () => {
	test("a prompt typed at the composer and response text both count as messages", async () => {
		const typed = rowEffect(
			userRow("prompt", { kind: "composer" }, [text(40)]),
			NO_CALLS,
		);
		const replied = rowEffect(responseRow(text(51)), NO_CALLS);

		expect(typed).toEqual({
			reset: false,
			counts: [{ id: "messages", chars: 40 }],
			agentCalls: [],
		});
		expect(replied.counts).toEqual([{ id: "messages", chars: 51 }]);
	});

	test("a prompt through the bridge is messages text", async () => {
		const effect = rowEffect(
			userRow("prompt", { kind: "bridge" }, [text(12)]),
			NO_CALLS,
		);

		expect(effect.counts).toEqual([{ id: "messages", chars: 12 }]);
	});

	for (const door of ["prompt", "delivery"] as const) {
		test(`a task notification naming a kept Agent call is agent reports text, through the ${door} door`, async () => {
			const body = notification(AGENT_CALL);
			const effect = rowEffect(
				userRow(door, NOTIFICATION, [{ type: "text", text: body }]),
				new Set([AGENT_CALL]),
			);

			expect(effect.counts).toEqual([{ id: "agents", chars: body.length }]);
		});
	}

	test("a task notification naming any other call is script results text", async () => {
		const body = notification(BASH_CALL);
		const effect = rowEffect(
			userRow("prompt", NOTIFICATION, [{ type: "text", text: body }]),
			new Set([AGENT_CALL]),
		);

		expect(effect.counts).toEqual([{ id: "scripts", chars: body.length }]);
	});

	test("a delivery the person queued at the composer is their own message", async () => {
		const effect = rowEffect(
			attachmentRow("delivery", { kind: "composer" }, [text(454)]),
			NO_CALLS,
		);

		expect(effect.counts).toEqual([{ id: "messages", chars: 454 }]);
	});

	test("a delivery from a scheduled trigger is script results text", async () => {
		const effect = rowEffect(
			attachmentRow("delivery", { kind: "scheduled-trigger" }, [text(61)]),
			NO_CALLS,
		);

		expect(effect.counts).toEqual([{ id: "scripts", chars: 61 }]);
	});

	test("a command row is command text", async () => {
		const effect = rowEffect(
			userRow("command", { kind: "unclassified" }, [text(217)]),
			NO_CALLS,
		);

		expect(effect.counts).toEqual([{ id: "commands", chars: 217 }]);
	});

	// `Bash` and `{"command":"ls"}`: 4 + 16 characters.
	test("a tool use is a call, its name and its input as JSON", async () => {
		const effect = rowEffect(
			responseRow({
				type: "tool_use",
				id: "toolu_1",
				name: "Bash",
				input: { command: "ls" },
			}),
			NO_CALLS,
		);

		expect(effect.counts).toEqual([{ id: "calls", chars: 20 }]);
	});

	// `Agent` and `{"prompt":"go"}`: 5 + 15 characters.
	test("an Agent tool use is an agent prompt, its name and its input as JSON", async () => {
		const effect = rowEffect(responseRow(agentUse(AGENT_CALL)), NO_CALLS);

		expect(effect.counts).toEqual([{ id: "prompts", chars: 20 }]);
	});

	test("a response's Agent tool uses are reported by id, and any other row reports none", async () => {
		const response = rowEffect(
			responseRow(
				text(5),
				agentUse(AGENT_CALL),
				{ type: "tool_use", id: BASH_CALL, name: "Bash", input: {} },
				agentUse("toolu_2"),
			),
			NO_CALLS,
		);
		const prompt = rowEffect(
			userRow("prompt", { kind: "composer" }, [text(5)]),
			NO_CALLS,
		);

		expect(response.agentCalls).toEqual([AGENT_CALL, "toolu_2"]);
		expect(prompt.agentCalls).toEqual([]);
	});

	for (const name of ["Write", "Edit", "NotebookEdit"]) {
		test(`a ${name} tool use is a file write, its name and its input as JSON`, async () => {
			const effect = rowEffect(
				responseRow({
					type: "tool_use",
					id: "toolu_3",
					name,
					input: { file_path: "a" },
				}),
				NO_CALLS,
			);

			expect(effect.counts).toEqual([
				{ id: "writes", chars: name.length + 17 },
			]);
		});
	}

	test("a thinking block counts nothing, whatever text it holds", async () => {
		const effect = rowEffect(
			responseRow({
				type: "thinking",
				thinking: "weigh the next step",
				signature: "s",
			}),
			NO_CALLS,
		);

		expect(effect.counts).toEqual([]);
	});

	test("image and document blocks count nothing beside the text they arrive with", async () => {
		const effect = rowEffect(
			userRow("prompt", { kind: "composer" }, [
				text(10),
				{ type: "image", source: { type: "base64", data: "AAAA" } },
				{ type: "document", source: { type: "text", data: "a document" } },
			]),
			NO_CALLS,
		);

		expect(effect.counts).toEqual([{ id: "messages", chars: 10 }]);
	});

	test("a Read result is read text, its string content measured", async () => {
		const effect = rowEffect(
			userRow("tool-result", READ, [
				{
					type: "tool_result",
					tool_use_id: "toolu_1",
					content: "y".repeat(300),
				},
			]),
			NO_CALLS,
		);

		expect(effect.counts).toEqual([{ id: "read", chars: 300 }]);
	});

	test("an Agent tool result is agent reports text", async () => {
		const effect = rowEffect(
			userRow("tool-result", AGENT, [
				{
					type: "tool_result",
					tool_use_id: AGENT_CALL,
					content: [text(1200)],
				},
			]),
			NO_CALLS,
		);

		expect(effect.counts).toEqual([{ id: "agents", chars: 1200 }]);
	});

	test("a row the Agent tool hands over beside its result is agent reports text", async () => {
		const effect = rowEffect(
			userRow("tool-message", AGENT, [text(70)]),
			NO_CALLS,
		);

		expect(effect.counts).toEqual([{ id: "agents", chars: 70 }]);
	});

	test("a Bash result is results text, the sum of its text blocks", async () => {
		const effect = rowEffect(
			userRow("tool-result", BASH, [
				{
					type: "tool_result",
					tool_use_id: "toolu_2",
					content: [
						text(100),
						{ type: "image", source: { type: "base64", data: "AAAA" } },
						text(20),
					],
				},
			]),
			NO_CALLS,
		);

		expect(effect.counts).toEqual([{ id: "results", chars: 120 }]);
	});

	test("a row a tool hands over beside its result is results text", async () => {
		const effect = rowEffect(
			userRow("tool-message", { kind: "tool", tool: "Skill" }, [text(70)]),
			NO_CALLS,
		);

		expect(effect.counts).toEqual([{ id: "results", chars: 70 }]);
	});

	test("a settings hook's context is hook output", async () => {
		const effect = rowEffect(
			attachmentRow(
				"hook-context",
				{ kind: "hook", event: "UserPromptSubmit" },
				[text(300)],
			),
			NO_CALLS,
		);

		expect(effect.counts).toEqual([{ id: "hooks", chars: 300 }]);
	});

	test("an attachment a hook authored is hook output", async () => {
		const effect = rowEffect(
			attachmentRow(
				"attachment",
				{ kind: "hook", event: "PostToolUse" },
				[text(45)],
				"hook_success",
			),
			NO_CALLS,
		);

		expect(effect.counts).toEqual([{ id: "hooks", chars: 45 }]);
	});

	for (const door of ["attachment", "note"] as const) {
		test(`a ${door} a plugin authored is plugin context`, async () => {
			const effect = rowEffect(
				attachmentRow(door, { kind: "plugin", event: "prompt.submit" }, [
					text(33),
				]),
				NO_CALLS,
			);

			expect(effect.counts).toEqual([{ id: "plugins", chars: 33 }]);
		});
	}

	for (const name of [
		"skill_listing",
		"instructions",
		"nested_memory",
		"mcp_instructions_delta",
		"agent_listing_delta",
	]) {
		test(`the ${name} attachment counts nothing, its breakdown row reports it`, async () => {
			const effect = rowEffect(
				attachmentRow("attachment", { kind: "engine" }, [text(500)], name),
				NO_CALLS,
			);

			expect(effect.counts).toEqual([]);
		});
	}

	for (const name of [
		"file",
		"edited_text_file",
		"compact_file_reference",
		"plan_file_reference",
	]) {
		test(`the ${name} attachment is an attached file`, async () => {
			const effect = rowEffect(
				attachmentRow("attachment", { kind: "engine" }, [text(80)], name),
				NO_CALLS,
			);

			expect(effect.counts).toEqual([{ id: "files", chars: 80 }]);
		});
	}

	test("any other engine attachment is a Claude Code reminder", async () => {
		const effect = rowEffect(
			attachmentRow(
				"attachment",
				{ kind: "engine" },
				[text(80)],
				"date_change",
			),
			NO_CALLS,
		);

		expect(effect.counts).toEqual([{ id: "reminders", chars: 80 }]);
	});

	test("an engine note is a Claude Code reminder", async () => {
		const effect = rowEffect(
			userRow("note", { kind: "engine" }, [text(29)]),
			NO_CALLS,
		);

		expect(effect.counts).toEqual([{ id: "reminders", chars: 29 }]);
	});

	test("a compaction replaces the window, its text the summary", async () => {
		const effect = rowEffect(
			userRow("compaction", { kind: "engine" }, [text(5000)]),
			NO_CALLS,
		);

		expect(effect).toEqual({
			reset: true,
			counts: [{ id: "summary", chars: 5000 }],
			agentCalls: [],
		});
	});

	test("a compaction no request carries still replaces the window", async () => {
		const effect = rowEffect(
			{
				door: "compaction",
				origin: { kind: "engine" },
				message: {
					type: "system",
					name: "compact_boundary",
					content: [text(22)],
				},
			},
			NO_CALLS,
		);

		expect(effect).toEqual({ reset: true, counts: [], agentCalls: [] });
	});

	test("a notice counts nothing", async () => {
		const effect = rowEffect(
			{
				door: "notice",
				origin: { kind: "engine" },
				message: {
					type: "system",
					name: "informational",
					content: [text(371)],
				},
			},
			NO_CALLS,
		);

		expect(effect).toEqual({ reset: false, counts: [], agentCalls: [] });
	});

	test("a queue record counts nothing", async () => {
		const effect = rowEffect(
			userRow("queue", { kind: "engine" }, [text(31)]),
			NO_CALLS,
		);

		expect(effect).toEqual({ reset: false, counts: [], agentCalls: [] });
	});

	test("an attachment no request carries counts nothing", async () => {
		const effect = rowEffect(
			{
				door: "attachment",
				origin: { kind: "engine" },
				message: {
					type: "attachment",
					name: "prompt_snapshot",
					content: [text(9)],
				},
			},
			NO_CALLS,
		);

		expect(effect.counts).toEqual([]);
	});
});

describe("adding counts to the estimates", () => {
	test("each count adds its characters to its category", async () => {
		const once = addCounts(NO_ESTIMATES, [
			{ id: "messages", chars: 40 },
			{ id: "writes", chars: 20 },
		]);
		const twice = addCounts(once, [{ id: "messages", chars: 2 }]);

		expect(twice).toEqual({
			summary: 0,
			hooks: 0,
			plugins: 0,
			reminders: 0,
			files: 0,
			messages: 42,
			scripts: 0,
			commands: 0,
			calls: 0,
			writes: 20,
			results: 0,
			read: 0,
			prompts: 0,
			agents: 0,
			thinking: 0,
		});
	});

	test("the estimates added to stay as they were", async () => {
		addCounts(NO_ESTIMATES, [{ id: "messages", chars: 40 }]);

		expect(NO_ESTIMATES.messages).toBe(0);
	});
});

const MODEL = "claude-opus-4-7";

/** The characters of every category that holds any, so a test names only what it expects. */
function charsOf(pieces: { chars: Readonly<Record<string, number>> }) {
	return Object.fromEntries(
		Object.entries(pieces.chars).filter(([, count]) => count > 0),
	);
}

function mediaOf(pieces: { media: Readonly<Record<string, number>> }) {
	return Object.fromEntries(
		Object.entries(pieces.media).filter(([, count]) => count > 0),
	);
}

function inputOf(row: Row, calls: ReadonlySet<string> = NO_CALLS) {
	return charsOf(rowPieces(row, calls, MODEL).input);
}

describe("what one kept row adds to the window", () => {
	const messageOrigins = [
		{ kind: "composer" },
		{ kind: "bridge" },
		{ kind: "slack-ping" },
		{ kind: "sdk" },
		{ kind: "auto-continuation" },
	] as const;
	for (const origin of messageOrigins) {
		test(`a prompt from ${origin.kind} shows under messages`, async () => {
			expect(inputOf(userRow("prompt", origin, [text(30)]))).toEqual({
				messages: 30,
			});
		});
	}

	test("a notification from a background task shows under background tasks", async () => {
		const body = notification(BASH_CALL);

		expect(
			inputOf(
				userRow("prompt", NOTIFICATION, [{ type: "text", text: body }]),
				new Set([AGENT_CALL]),
			),
		).toEqual({ tasks: body.length });
	});

	test("a notification from a kept Agent call shows under agent reports", async () => {
		const body = notification(AGENT_CALL);

		expect(
			inputOf(
				userRow("prompt", NOTIFICATION, [{ type: "text", text: body }]),
				new Set([AGENT_CALL]),
			),
		).toEqual({ agents: body.length });
	});

	test("a scheduled prompt firing shows under background tasks", async () => {
		expect(
			inputOf(
				attachmentRow("delivery", { kind: "scheduled-trigger" }, [text(61)]),
			),
		).toEqual({ tasks: 61 });
	});

	const relayedOrigins = [
		{ kind: "peer" },
		{ kind: "peer-send-message" },
		{ kind: "projects-relay" },
		{ kind: "coordinator" },
		{ kind: "observer" },
		{ kind: "observer-activity" },
		{ kind: "channel", server: "s" },
	] as const;
	for (const origin of relayedOrigins) {
		test(`text from ${origin.kind} shows under relayed messages`, async () => {
			expect(inputOf(userRow("prompt", origin, [text(25)]))).toEqual({
				relayed: 25,
			});
		});
	}

	test("an unclassified prompt the engine frames as non-user shows under Claude Code reminders", async () => {
		const row = userRow("prompt", { kind: "unclassified" }, [text(18)]);

		expect(
			inputOf({ ...row, message: { ...row.message, isMeta: true } }),
		).toEqual({ reminders: 18 });
	});

	test("an unclassified prompt with no such framing shows under relayed messages", async () => {
		expect(
			inputOf(userRow("prompt", { kind: "unclassified" }, [text(18)])),
		).toEqual({ relayed: 18 });
	});

	test("a plugin's prompt shows under plugin context", async () => {
		expect(
			inputOf(userRow("prompt", { kind: "plugin", name: "p" }, [text(9)])),
		).toEqual({ plugins: 9 });
	});

	test("a prompt the engine delivers into a running turn shows under Claude Code reminders", async () => {
		expect(inputOf(userRow("prompt", { kind: "engine" }, [text(14)]))).toEqual({
			reminders: 14,
		});
	});

	test("a hook's prompt shows under hook output", async () => {
		expect(
			inputOf(userRow("prompt", { kind: "hook", event: "h" }, [text(7)])),
		).toEqual({ hooks: 7 });
	});

	test("a prompt a tool handed over shows under that tool's results", async () => {
		expect(inputOf(userRow("prompt", BASH, [text(33)]))).toEqual({
			results: 33,
		});
	});

	test("nothing shows under a retired script results row, whichever origin the text has", async () => {
		const origins: Row["origin"][] = [
			...messageOrigins,
			...relayedOrigins,
			NOTIFICATION,
			{ kind: "scheduled-trigger" },
			{ kind: "unclassified" },
			{ kind: "engine" },
		];
		for (const origin of origins) {
			expect(inputOf(userRow("prompt", origin, [text(5)]))).not.toHaveProperty(
				"scripts",
			);
		}
	});

	test("a queued_command holding a typed prompt shows as messages", async () => {
		expect(
			inputOf(
				attachmentRow(
					"attachment",
					{ kind: "engine" },
					[text(44)],
					"queued_command",
				),
			),
		).toEqual({ messages: 44 });
	});

	test("a queued_command holding a background task's notification shows under background tasks", async () => {
		const body = notification(BASH_CALL);

		expect(
			inputOf(
				attachmentRow(
					"attachment",
					{ kind: "engine" },
					[{ type: "text", text: body }],
					"queued_command",
				),
			),
		).toEqual({ tasks: body.length });
	});

	test("a response's text and tool calls show as its visible output, never as input", async () => {
		const pieces = rowPieces(
			responseRow(text(40), agentUse(AGENT_CALL, "go")),
			NO_CALLS,
			MODEL,
		);

		expect(charsOf(pieces.input)).toEqual({});
		expect(charsOf(pieces.output?.visible ?? { chars: {} })).toEqual({
			messages: 40,
			prompts: "Agent".length + JSON.stringify({ prompt: "go" }).length,
		});
		expect(pieces.agentCalls).toEqual([AGENT_CALL]);
	});

	test("a response's thinking block marks it as thinking and adds no characters", async () => {
		const pieces = rowPieces(
			responseRow({ type: "thinking", thinking: "weigh it", signature: "s" }),
			NO_CALLS,
			MODEL,
		);

		expect(pieces.output?.thinking).toBe(true);
		expect(charsOf(pieces.output?.visible ?? { chars: {} })).toEqual({});
	});

	test("a response with no thinking block is not marked as thinking", async () => {
		const pieces = rowPieces(responseRow(text(4)), NO_CALLS, MODEL);

		expect(pieces.output?.thinking).toBe(false);
	});

	test("a server tool's result inside a response shows under tool results as served output", async () => {
		const pieces = rowPieces(
			responseRow({
				type: "web_search_tool_result",
				tool_use_id: "srvtoolu_1",
				content: [{ type: "text", text: "x".repeat(70) }],
			}),
			NO_CALLS,
			MODEL,
		);

		expect(charsOf(pieces.output?.served ?? { chars: {} })).toEqual({
			results: 70,
		});
		expect(charsOf(pieces.output?.visible ?? { chars: {} })).toEqual({});
	});

	test("a tool_reference in a ToolSearch result shows under tool results", async () => {
		const reference = { type: "tool_reference", tool_name: "mcp__x__y" };
		const row = userRow("tool-result", { kind: "tool", tool: "ToolSearch" }, [
			{ type: "tool_result", tool_use_id: "t", content: [reference] },
		]);

		expect(inputOf(row)).toEqual({ results: JSON.stringify(reference).length });
	});

	test("a block of a kind the gauge does not know shows its JSON length in its row's category", async () => {
		const unknown = { type: "future_block", payload: "abc" };

		expect(inputOf(userRow("prompt", { kind: "composer" }, [unknown]))).toEqual(
			{ messages: JSON.stringify(unknown).length },
		);
	});

	test("an image a Read returns shows as file-read tokens, not characters", async () => {
		const row = userRow("tool-result", READ, [
			{
				type: "tool_result",
				tool_use_id: "t",
				content: [{ type: "image", source: { type: "base64", data: "AAAA" } }],
			},
		]);
		const pieces = rowPieces(row, NO_CALLS, MODEL);

		expect(charsOf(pieces.input)).toEqual({});
		expect(mediaOf(pieces.input)).toEqual({ read: 4784 });
	});

	test("a row with no role adds nothing", async () => {
		const pieces = rowPieces(
			{
				door: "attachment",
				origin: { kind: "engine" },
				message: {
					type: "attachment",
					name: "prompt_snapshot",
					content: [text(9)],
				},
			},
			NO_CALLS,
			MODEL,
		);

		expect(charsOf(pieces.input)).toEqual({});
		expect(pieces.output).toBeNull();
		expect(pieces.agentCalls).toEqual([]);
	});
});
