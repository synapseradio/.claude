/** What each row appended to the conversation adds to the gauge's message estimates, sorted by the door it came in by. */

import type { ApiContentBlock, SessionAppendInput } from "claude-code";

import type { MessageEstimates } from "../types";

/** A message category the gauge counts characters into. */
export type CountedId = keyof MessageEstimates;

/** Characters one row adds to one category. */
export type Counted = { id: CountedId; chars: number };

/** What one appended row adds: its counts, and whether it replaces the window (a compaction). */
export type RowEffect = { reset: boolean; counts: readonly Counted[] };

type Row = Pick<SessionAppendInput, "door" | "origin" | "message">;

type BlockKind =
	| "text"
	| "tool_use"
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
		return {
			kind: FILE_WRITERS.has(name) ? "file_write" : "tool_use",
			chars: name.length + jsonChars(input),
		};
	if (type === "tool_result")
		return { kind: "tool_result", chars: resultChars(content) };
	return { kind: "unmeasured", chars: 0 };
}

function sender({ origin }: Row): CountedId {
	return origin.kind === "composer" || origin.kind === "bridge"
		? "user"
		: "senders";
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

function category(row: Row, kind: BlockKind): CountedId | null {
	const { origin } = row;
	switch (row.door) {
		case "prompt":
		case "delivery":
			return sender(row);
		case "command":
			return "commands";
		case "response":
			if (kind === "text") return "replies";
			if (kind === "file_write") return "writes";
			return kind === "tool_use" ? "calls" : null;
		case "tool-result":
		case "tool-message":
			return origin.kind === "tool" && origin.tool === "Read"
				? "read"
				: "results";
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

/** What one appended row adds to the estimates; a row no request carries adds nothing. */
export function rowEffect(row: Row): RowEffect {
	const reset = row.door === "compaction";
	if (row.message.role === undefined) return { reset, counts: [] };
	const counts = row.message.content
		.map(measure)
		.flatMap(({ kind, chars }): Counted[] => {
			const id = category(row, kind);
			return id === null || chars === 0 ? [] : [{ id, chars }];
		});
	return { reset, counts };
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
		user: added("user"),
		senders: added("senders"),
		commands: added("commands"),
		calls: added("calls"),
		writes: added("writes"),
		results: added("results"),
		read: added("read"),
		thinking: added("thinking"),
		replies: added("replies"),
	};
}
