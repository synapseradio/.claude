/** What each row appended to the conversation adds to the gauge's message estimates, sorted by the door it came in by. */

import type { ApiContentBlock, SessionAppendInput } from "claude-code";

import type {
	MessageEstimates,
	OutputPieces,
	CountedId as PieceId,
	Pieces,
	RowPieces,
	Tally,
} from "../types";
import { measureBlock } from "./measure";

/** A message category the gauge counts characters into. */
export type CountedId = keyof MessageEstimates;

/** The categories the estimates and the pieces both name, so one routing serves both. */
type SharedId = Extract<CountedId, PieceId>;

/** Characters one row adds to one category. */
export type Counted = { id: CountedId; chars: number };

/** What one appended row adds: its counts, whether it replaces the window (a compaction), and the ids of the Agent calls it holds. */
export type RowEffect = {
	reset: boolean;
	counts: readonly Counted[];
	agentCalls: readonly string[];
};

type Row = Pick<SessionAppendInput, "door" | "origin" | "message">;

type Measured =
	| { kind: "text" | "tool_result" | "unmeasured"; chars: number }
	| { kind: "tool_use"; tool: string; chars: number };

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
	{ call: SharedId; result: SharedId }
> = new Map([
	["Write", { call: "writes", result: "results" }],
	["Edit", { call: "writes", result: "results" }],
	["NotebookEdit", { call: "writes", result: "results" }],
	["Read", { call: "calls", result: "read" }],
	[AGENT_TOOL, { call: "prompts", result: "agents" }],
]);

function jsonChars(value: unknown): number {
	return value === undefined ? 0 : JSON.stringify(value).length;
}

function textChars(item: unknown): number {
	if (typeof item !== "object" || item === null) return 0;
	if (!("type" in item && "text" in item)) return 0;
	return item.type === "text" && typeof item.text === "string"
		? item.text.length
		: 0;
}

function resultChars(content: unknown): number {
	if (typeof content === "string") return content.length;
	if (!Array.isArray(content)) return 0;
	return content.reduce(
		(sum: number, item: unknown) => sum + textChars(item),
		0,
	);
}

function measure(block: ApiContentBlock): Measured {
	const { type, text, name, input, content } = block;
	if (type === "text" && typeof text === "string")
		return { kind: "text", chars: text.length };
	if (type === "tool_use" && typeof name === "string")
		return {
			kind: "tool_use",
			tool: name,
			chars: name.length + jsonChars(input),
		};
	if (type === "tool_result")
		return { kind: "tool_result", chars: resultChars(content) };
	return { kind: "unmeasured", chars: 0 };
}

/** The tool-use id a task notification's text names, or undefined where none does. */
function notifiedCall({ message }: Row): string | undefined {
	for (const { type, text } of message.content) {
		if (type !== "text" || typeof text !== "string") continue;
		const id = NOTIFIED_CALL.exec(text)?.[1];
		if (id !== undefined) return id;
	}
	return undefined;
}

function sender(row: Row, agentCalls: ReadonlySet<string>): CountedId {
	const { kind } = row.origin;
	if (kind === "composer" || kind === "bridge") return "messages";
	if (kind !== "task-notification") return "scripts";
	const call = notifiedCall(row);
	return call !== undefined && agentCalls.has(call) ? "agents" : "scripts";
}

function toolResult({ origin }: Row): SharedId {
	if (origin.kind !== "tool") return "results";
	return TOOL_CATEGORIES.get(origin.tool)?.result ?? "results";
}

function response(block: Measured): CountedId | null {
	if (block.kind === "text") return "messages";
	if (block.kind !== "tool_use") return null;
	return TOOL_CATEGORIES.get(block.tool)?.call ?? "calls";
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

function injected({ origin, message }: Row): SharedId | null {
	if (origin.kind === "hook") return "hooks";
	if (origin.kind === "plugin") return "plugins";
	if (origin.kind !== "engine") return "reminders";
	const { name } = message;
	if (name !== undefined && BREAKDOWN_OWNED.has(name)) return null;
	return name !== undefined && FILE_ATTACHMENTS.has(name)
		? "files"
		: "reminders";
}

function category(
	row: Row,
	block: Measured,
	agentCalls: ReadonlySet<string>,
): CountedId | null {
	switch (row.door) {
		case "prompt":
		case "delivery":
			return sender(row, agentCalls);
		case "command":
			return "commands";
		case "response":
			return response(block);
		case "tool-result":
		case "tool-message":
			return toolResult(row);
		case "hook-context":
		case "attachment":
		case "note":
			return injected(row);
		case "compaction":
			return "summary";
		case "notice":
		case "queue":
			return null;
	}
}

/** What one appended row adds to the estimates, given the ids of the Agent calls kept before it; a row no request carries adds nothing. */
export function rowEffect(
	row: Row,
	agentCalls: ReadonlySet<string>,
): RowEffect {
	const reset = row.door === "compaction";
	if (row.message.role === undefined)
		return { reset, counts: [], agentCalls: [] };
	const counts = row.message.content
		.map(measure)
		.flatMap((block): Counted[] => {
			const id = category(row, block, agentCalls);
			return id === null || block.chars === 0
				? []
				: [{ id, chars: block.chars }];
		});
	return { reset, counts, agentCalls: agentCallsOf(row) };
}

/** The estimates with each count's characters added to its category. */
export function addCounts(
	e: MessageEstimates,
	counts: readonly Counted[],
): MessageEstimates {
	if (counts.length === 0) return e;
	const added = (id: CountedId): number =>
		counts.reduce((sum, c) => (c.id === id ? sum + c.chars : sum), e[id]);
	return {
		summary: added("summary"),
		hooks: added("hooks"),
		plugins: added("plugins"),
		reminders: added("reminders"),
		files: added("files"),
		messages: added("messages"),
		scripts: added("scripts"),
		commands: added("commands"),
		calls: added("calls"),
		writes: added("writes"),
		results: added("results"),
		read: added("read"),
		prompts: added("prompts"),
		agents: added("agents"),
		thinking: added("thinking"),
	};
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
	id: PieceId,
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
function queuedPrompt(row: Row, agentCalls: ReadonlySet<string>): PieceId {
	const call = notifiedCall(row);
	if (call !== undefined) return agentCalls.has(call) ? "agents" : "tasks";
	return textOf(row).includes("<task-notification>") ? "tasks" : "messages";
}

function promptCategory(row: Row, agentCalls: ReadonlySet<string>): PieceId {
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
): PieceId | null {
	if (row.origin.kind === "engine" && row.message.name === QUEUED_COMMAND)
		return queuedPrompt(row, agentCalls);
	return injected(row);
}

function inputCategory(
	row: Row,
	agentCalls: ReadonlySet<string>,
): PieceId | null {
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

function callCategory(block: ApiContentBlock): PieceId {
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
