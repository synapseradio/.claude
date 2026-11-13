import type { ApiContentBlock, SessionAppendInput } from "claude-code";
import { describe, expect, test } from "claude-code/testing";

import { addCounts, rowEffect } from "../hooks/counting";
import { NO_ESTIMATES } from "../hooks/rows";

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

function responseRow(block: ApiContentBlock): Row {
	return {
		door: "response",
		origin: { kind: "model", model: "test" },
		message: { type: "assistant", role: "assistant", content: [block] },
	};
}

function text(chars: number): ApiContentBlock {
	return { type: "text", text: "x".repeat(chars) };
}

const READ: Row["origin"] = { kind: "tool", tool: "Read" };
const BASH: Row["origin"] = { kind: "tool", tool: "Bash" };

describe("what one appended row counts", () => {
	test("a prompt typed at the composer is user text", async () => {
		const effect = rowEffect(
			userRow("prompt", { kind: "composer" }, [text(40)]),
		);

		expect(effect).toEqual({
			reset: false,
			counts: [{ id: "user", chars: 40 }],
		});
	});

	test("a prompt through the bridge is user text", async () => {
		const effect = rowEffect(userRow("prompt", { kind: "bridge" }, [text(12)]));

		expect(effect.counts).toEqual([{ id: "user", chars: 12 }]);
	});

	test("a prompt from a task notification is another sender's message", async () => {
		const effect = rowEffect(
			userRow("prompt", { kind: "task-notification" }, [text(900)]),
		);

		expect(effect.counts).toEqual([{ id: "senders", chars: 900 }]);
	});

	test("a delivery the person queued at the composer is their own message", async () => {
		const effect = rowEffect(
			attachmentRow("delivery", { kind: "composer" }, [text(454)]),
		);

		expect(effect.counts).toEqual([{ id: "user", chars: 454 }]);
	});

	test("a delivery from a scheduled trigger is another sender's message", async () => {
		const effect = rowEffect(
			attachmentRow("delivery", { kind: "scheduled-trigger" }, [text(61)]),
		);

		expect(effect.counts).toEqual([{ id: "senders", chars: 61 }]);
	});

	test("a command row is command text", async () => {
		const effect = rowEffect(
			userRow("command", { kind: "unclassified" }, [text(217)]),
		);

		expect(effect.counts).toEqual([{ id: "commands", chars: 217 }]);
	});

	test("response text is a reply", async () => {
		expect(rowEffect(responseRow(text(51))).counts).toEqual([
			{ id: "replies", chars: 51 },
		]);
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
		);

		expect(effect.counts).toEqual([{ id: "calls", chars: 20 }]);
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
		);

		expect(effect.counts).toEqual([{ id: "user", chars: 10 }]);
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
		);

		expect(effect.counts).toEqual([{ id: "read", chars: 300 }]);
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
		);

		expect(effect.counts).toEqual([{ id: "results", chars: 120 }]);
	});

	test("a row a tool hands over beside its result is results text", async () => {
		const effect = rowEffect(
			userRow("tool-message", { kind: "tool", tool: "Skill" }, [text(70)]),
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
		);

		expect(effect.counts).toEqual([{ id: "hooks", chars: 45 }]);
	});

	for (const door of ["attachment", "note"] as const) {
		test(`a ${door} a plugin authored is plugin context`, async () => {
			const effect = rowEffect(
				attachmentRow(door, { kind: "plugin", event: "prompt.submit" }, [
					text(33),
				]),
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
		);

		expect(effect.counts).toEqual([{ id: "reminders", chars: 80 }]);
	});

	test("an engine note is a Claude Code reminder", async () => {
		const effect = rowEffect(userRow("note", { kind: "engine" }, [text(29)]));

		expect(effect.counts).toEqual([{ id: "reminders", chars: 29 }]);
	});

	test("a compaction replaces the window, its text the summary", async () => {
		const effect = rowEffect(
			userRow("compaction", { kind: "engine" }, [text(5000)]),
		);

		expect(effect).toEqual({
			reset: true,
			counts: [{ id: "summary", chars: 5000 }],
		});
	});

	test("a compaction no request carries still replaces the window", async () => {
		const effect = rowEffect({
			door: "compaction",
			origin: { kind: "engine" },
			message: {
				type: "system",
				name: "compact_boundary",
				content: [text(22)],
			},
		});

		expect(effect).toEqual({ reset: true, counts: [] });
	});

	test("a notice counts nothing", async () => {
		const effect = rowEffect({
			door: "notice",
			origin: { kind: "engine" },
			message: { type: "system", name: "informational", content: [text(371)] },
		});

		expect(effect).toEqual({ reset: false, counts: [] });
	});

	test("a queue record counts nothing", async () => {
		const effect = rowEffect(userRow("queue", { kind: "engine" }, [text(31)]));

		expect(effect).toEqual({ reset: false, counts: [] });
	});

	test("an attachment no request carries counts nothing", async () => {
		const effect = rowEffect({
			door: "attachment",
			origin: { kind: "engine" },
			message: {
				type: "attachment",
				name: "prompt_snapshot",
				content: [text(9)],
			},
		});

		expect(effect.counts).toEqual([]);
	});
});

describe("adding counts to the estimates", () => {
	test("each count adds its characters to its category", async () => {
		const once = addCounts(NO_ESTIMATES, [
			{ id: "user", chars: 40 },
			{ id: "writes", chars: 20 },
		]);
		const twice = addCounts(once, [{ id: "user", chars: 2 }]);

		expect(twice).toEqual({
			summary: 0,
			hooks: 0,
			plugins: 0,
			reminders: 0,
			files: 0,
			user: 42,
			senders: 0,
			commands: 0,
			calls: 0,
			writes: 20,
			results: 0,
			read: 0,
			thinking: 0,
			replies: 0,
		});
	});

	test("the estimates added to stay as they were", async () => {
		addCounts(NO_ESTIMATES, [{ id: "user", chars: 40 }]);

		expect(NO_ESTIMATES.user).toBe(0);
	});
});
