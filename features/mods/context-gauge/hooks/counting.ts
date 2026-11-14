/** What each row appended to the conversation adds to the gauge's message estimates, sorted by the door it came in by. */

import type { ApiContentBlock, SessionAppendInput } from "claude-code";

import type { MessageEstimates } from "../types";

/** A message category the gauge counts characters into. */
export type CountedId = keyof MessageEstimates;

/** Characters one row adds to one category. */
export type Counted = { id: CountedId; chars: number };

/** What one appended row adds: its counts, whether it replaces the window (a compaction), and the ids of the Agent calls it holds. */
export type RowEffect = {
	reset: boolean;
	counts: readonly Counted[];
	agentCalls: readonly string[];
};

type Row = Pick<SessionAppendInput, "door" | "origin" | "message">;

type BlockKind =
	| "text"
	| "tool_use"
	| "agent_call"
	| "file_write"
	| "tool_result"
	| "unmeasured";

type Measured = { kind: BlockKind; chars: number };

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

/** Tools whose calls write a file. */
export const FILE_WRITERS: ReadonlySet<string> = new Set([
	"Write",
	"Edit",
	"NotebookEdit",
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
		return { kind: callKind(name), chars: name.length + jsonChars(input) };
	if (type === "tool_result")
		return { kind: "tool_result", chars: resultChars(content) };
	return { kind: "unmeasured", chars: 0 };
}

function callKind(name: string): BlockKind {
	if (name === AGENT_TOOL) return "agent_call";
	return FILE_WRITERS.has(name) ? "file_write" : "tool_use";
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

function toolResult({ origin }: Row): CountedId {
	if (origin.kind !== "tool") return "results";
	if (origin.tool === AGENT_TOOL) return "agents";
	return origin.tool === "Read" ? "read" : "results";
}

function response(kind: BlockKind): CountedId | null {
	switch (kind) {
		case "text":
			return "messages";
		case "agent_call":
			return "prompts";
		case "file_write":
			return "writes";
		case "tool_use":
			return "calls";
		case "tool_result":
		case "unmeasured":
			return null;
	}
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

function category(
	row: Row,
	kind: BlockKind,
	agentCalls: ReadonlySet<string>,
): CountedId | null {
	switch (row.door) {
		case "prompt":
		case "delivery":
			return sender(row, agentCalls);
		case "command":
			return "commands";
		case "response":
			return response(kind);
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
		.flatMap(({ kind, chars }): Counted[] => {
			const id = category(row, kind, agentCalls);
			return id === null || chars === 0 ? [] : [{ id, chars }];
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
