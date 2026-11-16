import type { ApiContentBlock, SessionAppendInput } from "claude-code";
import { describe, expect, test } from "claude-code/testing";

import { rowPieces } from "../hooks/counting";
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
const NOTIFICATION: Row["origin"] = { kind: "task-notification" };

/** Nothing kept: no Agent call seen yet. */
const NO_CALLS: ReadonlySet<string> = new Set();

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
