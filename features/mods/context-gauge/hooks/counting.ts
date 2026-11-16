/** What each row appended to the conversation adds to the gauge's message categories, sorted by the door it came in by. */

import type { ApiContentBlock, SessionAppendInput } from "claude-code";

import type {
	CountedId,
	OutputPieces,
	Pieces,
	RowPieces,
	Tally,
} from "../types";
import { measureBlock } from "./measure";

type Row = Pick<SessionAppendInput, "door" | "origin" | "message">;

/** Attachment names whose text a breakdown row already reports, so counting them again would double it. */
export const BREAKDOWN_OWNED: ReadonlySet<string> = new Set([
	"skill_listing",
	"instructions",
	"nested_memory",
	"mcp_instructions_delta",
	"agent_listing_delta",
]);

/** Attachment names that carry the text of a file. */
export const FILE_ATTACHMENTS: ReadonlySet<string> = new Set([
	"file",
	"edited_text_file",
	"compact_file_reference",
	"plan_file_reference",
]);

/** The tool that starts a subagent. */
const AGENT_TOOL = "Agent";

/** Where a task notification's text names the tool use that started its task. */
const NOTIFIED_CALL = /<tool-use-id>([^<]+)<\/tool-use-id>/u;

/** Where a tool's calls and results count, for each tool counted apart from the rest; any other tool's count as tool calls and tool results. */
const TOOL_CATEGORIES: ReadonlyMap<
	string,
	{ call: CountedId; result: CountedId }
> = new Map([
	["Write", { call: "writes", result: "results" }],
	["Edit", { call: "writes", result: "results" }],
	["NotebookEdit", { call: "writes", result: "results" }],
	["Read", { call: "calls", result: "read" }],
	[AGENT_TOOL, { call: "prompts", result: "agents" }],
]);

/** The tool-use id a task notification's text names, or undefined where none does. */
function notifiedCall({ message }: Row): string | undefined {
	for (const { type, text } of message.content) {
		if (type !== "text" || typeof text !== "string") continue;
		const id = NOTIFIED_CALL.exec(text)?.[1];
		if (id !== undefined) return id;
	}
	return undefined;
}

function toolResult({ origin }: Row): CountedId {
	if (origin.kind !== "tool") return "results";
	return TOOL_CATEGORIES.get(origin.tool)?.result ?? "results";
}

/** The ids of a response's Agent calls; none for any other row. */
function agentCallsOf({ door, message }: Row): string[] {
	if (door !== "response") return [];
	return message.content.flatMap(({ type, name, id }) =>
		type === "tool_use" && name === AGENT_TOOL && typeof id === "string"
			? [id]
			: [],
	);
}

function injected({ origin, message }: Row): CountedId | null {
	if (origin.kind === "hook") return "hooks";
	if (origin.kind === "plugin") return "plugins";
	if (origin.kind !== "engine") return "reminders";
	const { name } = message;
	if (name !== undefined && BREAKDOWN_OWNED.has(name)) return null;
	return name !== undefined && FILE_ATTACHMENTS.has(name)
		? "files"
		: "reminders";
}

const NO_TALLY: Tally = {
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

const NO_PIECES: Pieces = { chars: NO_TALLY, media: NO_TALLY };

/** The attachment that carries a prompt delivered into a running turn. */
const QUEUED_COMMAND = "queued_command";

/** Block kinds a response carries for a tool the server ran itself. */
const SERVED_RESULT_SUFFIX = "_tool_result";

function addMeasured(
	pieces: Pieces,
	id: CountedId,
	measured: { chars: number } | { media: number },
): Pieces {
	if ("chars" in measured)
		return measured.chars === 0
			? pieces
			: {
					...pieces,
					chars: { ...pieces.chars, [id]: pieces.chars[id] + measured.chars },
				};
	return measured.media === 0
		? pieces
		: {
				...pieces,
				media: { ...pieces.media, [id]: pieces.media[id] + measured.media },
			};
}

function textOf({ message }: Row): string {
	return message.content
		.map(({ type, text }) =>
			type === "text" && typeof text === "string" ? text : "",
		)
		.join("\n");
}

/** Where a prompt delivered into a running turn counts: a notification for an Agent call, any other notification, or the person's words. */
function queuedPrompt(row: Row, agentCalls: ReadonlySet<string>): CountedId {
	const call = notifiedCall(row);
	if (call !== undefined) return agentCalls.has(call) ? "agents" : "tasks";
	return textOf(row).includes("<task-notification>") ? "tasks" : "messages";
}

function promptCategory(row: Row, agentCalls: ReadonlySet<string>): CountedId {
	switch (row.origin.kind) {
		case "composer":
		case "bridge":
		case "slack-ping":
		case "sdk":
		case "auto-continuation":
		case "model":
			return "messages";
		case "task-notification":
			return queuedPrompt(row, agentCalls) === "agents" ? "agents" : "tasks";
		case "scheduled-trigger":
			return "tasks";
		case "peer":
		case "peer-send-message":
		case "projects-relay":
		case "coordinator":
		case "observer":
		case "observer-activity":
		case "channel":
			return "relayed";
		case "unclassified":
			return row.message.isMeta === true ? "reminders" : "relayed";
		case "plugin":
			return "plugins";
		case "engine":
			return "reminders";
		case "hook":
			return "hooks";
		case "tool":
			return toolResult(row);
	}
}

function attachedCategory(
	row: Row,
	agentCalls: ReadonlySet<string>,
): CountedId | null {
	if (row.origin.kind === "engine" && row.message.name === QUEUED_COMMAND)
		return queuedPrompt(row, agentCalls);
	return injected(row);
}

function inputCategory(
	row: Row,
	agentCalls: ReadonlySet<string>,
): CountedId | null {
	switch (row.door) {
		case "prompt":
		case "delivery":
			return promptCategory(row, agentCalls);
		case "command":
			return "commands";
		case "tool-result":
		case "tool-message":
			return toolResult(row);
		case "hook-context":
		case "attachment":
		case "note":
			return attachedCategory(row, agentCalls);
		case "compaction":
			return "summary";
		case "response":
		case "notice":
		case "queue":
			return null;
	}
}

function callCategory(block: ApiContentBlock): CountedId {
	const { type, name } = block;
	const isCall =
		type === "tool_use" ||
		type === "server_tool_use" ||
		type === "mcp_tool_use";
	if (!isCall || typeof name !== "string") return "messages";
	return TOOL_CATEGORIES.get(name)?.call ?? "calls";
}

function outputOf(
	blocks: readonly ApiContentBlock[],
	model: string,
): OutputPieces {
	return blocks.reduce<OutputPieces>(
		(output, block) => {
			const { type } = block;
			if (type === "thinking" || type === "redacted_thinking")
				return { ...output, thinking: true };
			const measured = measureBlock(block, model);
			if (type.endsWith(SERVED_RESULT_SUFFIX))
				return {
					...output,
					served: addMeasured(output.served, "results", measured),
				};
			return {
				...output,
				visible: addMeasured(output.visible, callCategory(block), measured),
			};
		},
		{ visible: NO_PIECES, thinking: false, served: NO_PIECES },
	);
}

/** What one kept row adds to a window: its blocks measured by kind into the category its origin names, a response's into its output; a row no request carries adds nothing. */
export function rowPieces(
	row: Row,
	agentCalls: ReadonlySet<string>,
	model: string,
): RowPieces {
	if (row.message.role === undefined)
		return { input: NO_PIECES, output: null, agentCalls: [] };
	if (row.door === "response")
		return {
			input: NO_PIECES,
			output: outputOf(row.message.content, model),
			agentCalls: agentCallsOf(row),
		};
	const id = inputCategory(row, agentCalls);
	const input =
		id === null
			? NO_PIECES
			: row.message.content.reduce(
					(pieces, block) =>
						addMeasured(pieces, id, measureBlock(block, model)),
					NO_PIECES,
				);
	return { input, output: null, agentCalls: [] };
}
