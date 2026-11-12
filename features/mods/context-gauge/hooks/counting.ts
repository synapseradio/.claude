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

/** The block kinds the gauge tells apart; every other kind is `unmeasured`. */
type BlockKind = "text" | "tool_use" | "tool_result" | "unmeasured";

/** A content block's kind and the characters the model reads in it. */
type Measured = { kind: BlockKind; chars: number };

/** Characters of `value` as JSON, 0 where there is none. */
function jsonChars(value: unknown): number {
	return value === undefined ? 0 : JSON.stringify(value).length;
}

/** Characters of a text block held as an unknown value, 0 for any other value. */
function textChars(item: unknown): number {
	if (typeof item !== "object" || item === null) return 0;
	if (!("type" in item && "text" in item)) return 0;
	return item.type === "text" && typeof item.text === "string"
		? item.text.length
		: 0;
}

/** Characters of a tool result's content: the string, or the sum of its text blocks. */
function resultChars(content: unknown): number {
	if (typeof content === "string") return content.length;
	if (!Array.isArray(content)) return 0;
	return content.reduce(
		(sum: number, item: unknown) => sum + textChars(item),
		0,
	);
}

/** Sorts a block by kind and measures it; thinking, media and unknown kinds measure 0. */
function measure(block: ApiContentBlock): Measured {
	const { type, text, name, input, content } = block;
	if (type === "text" && typeof text === "string")
		return { kind: "text", chars: text.length };
	if (type === "tool_use" && typeof name === "string")
		return { kind: "tool_use", chars: name.length + jsonChars(input) };
	if (type === "tool_result")
		return { kind: "tool_result", chars: resultChars(content) };
	return { kind: "unmeasured", chars: 0 };
}

/** The category a block of `row` counts into, or null where it counts nowhere. */
function category(row: Row, kind: BlockKind): CountedId | null {
	const { origin } = row;
	switch (row.door) {
		case "prompt":
			return origin.kind === "composer" || origin.kind === "bridge"
				? "user"
				: "deliveries";
		case "delivery":
			return "deliveries";
		case "command":
			return "commands";
		case "response":
			if (kind === "text") return "replies";
			return kind === "tool_use" ? "calls" : null;
		case "tool-result":
		case "tool-message":
			return origin.kind === "tool" && origin.tool === "Read"
				? "read"
				: "results";
		case "hook-context":
			return "hooks";
		case "attachment":
		case "note":
			return "attachments";
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
	const added = (id: CountedId): number =>
		counts.reduce((sum, c) => (c.id === id ? sum + c.chars : sum), e[id]);
	return {
		summary: added("summary"),
		hooks: added("hooks"),
		attachments: added("attachments"),
		user: added("user"),
		commands: added("commands"),
		deliveries: added("deliveries"),
		calls: added("calls"),
		results: added("results"),
		read: added("read"),
		thinking: added("thinking"),
		replies: added("replies"),
	};
}
