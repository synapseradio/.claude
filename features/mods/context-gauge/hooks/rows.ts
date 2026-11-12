/** The gauge's rows: the engine's breakdown rows named, merged and ordered, its Messages row split by the gauge's estimates. */

import type { MessageEstimates, UsageCategory } from "../types";
import type { CountedId } from "./counting";
import type { CategoryId } from "./palette";
import { BAR_ORDER } from "./palette";

const CHARS_PER_TOKEN = 4;

type NamedId = Exclude<CategoryId, "other">;

/** The gauge's category for each breakdown row name the engine reports. */
const ROW_IDS: ReadonlyMap<string, NamedId> = new Map([
	["System prompt", "system"],
	["System tools", "system"],
	["MCP tools", "mcp"],
	["MCP server instructions", "mcp"],
	["Custom agents", "agents"],
	["Memory files", "memory"],
	["Skills", "skills"],
]);

/** Estimates before anything is counted, and after `/clear` or compaction. */
export const NO_ESTIMATES: MessageEstimates = {
	summary: 0,
	hooks: 0,
	attachments: 0,
	user: 0,
	commands: 0,
	deliveries: 0,
	calls: 0,
	results: 0,
	read: 0,
	thinking: 0,
	replies: 0,
};

function isCounted(id: CategoryId): id is CountedId {
	return id in NO_ESTIMATES;
}

/** The Messages row's counted parts, in bar order. */
const COUNTED: readonly CountedId[] = BAR_ORDER.filter(isCounted);

/** Each category's place in the bar. */
const BAR_RANK: ReadonlyMap<string, number> = new Map(
	BAR_ORDER.map((id, rank) => [id, rank]),
);

export type GaugeRow = {
	id: CategoryId;
	label: string;
	tokens: number;
	estimated: boolean;
};

function named(id: NamedId, tokens: number, estimated: boolean): GaugeRow {
	return { id, label: id, tokens, estimated };
}

function splitMessages(tokens: number, chars: MessageEstimates): GaugeRow[] {
	const seen =
		COUNTED.reduce((sum, id) => sum + chars[id], 0) / CHARS_PER_TOKEN;
	const scale = seen > tokens ? tokens / seen : 1;
	const counted = COUNTED.map((id) =>
		named(id, Math.round((chars[id] / CHARS_PER_TOKEN) * scale), true),
	);
	const sum = counted.reduce((total, r) => total + r.tokens, 0);
	const rest = scale < 1 ? 0 : Math.max(0, tokens - sum);
	return counted.concat(named("unattributed", rest, false));
}

/** Sums the tokens of rows sharing an id and label, keeping the first one's place. */
function merged(rows: readonly GaugeRow[]): GaugeRow[] {
	const byKey = new Map<string, GaugeRow>();
	for (const r of rows) {
		const key = `${r.id}\u0000${r.label}`;
		const seen = byKey.get(key);
		byKey.set(key, seen ? { ...seen, tokens: seen.tokens + r.tokens } : r);
	}
	return Array.from(byKey.values());
}

/** The rows the gauge draws, in bar order, each with tokens. */
export function gaugeRows(
	categories: readonly UsageCategory[],
	chars: MessageEstimates,
): GaugeRow[] {
	const rows = categories.flatMap((c): GaugeRow[] => {
		if (c.name === "Messages") return splitMessages(c.tokens, chars);
		const id = ROW_IDS.get(c.name);
		if (id) return [named(id, c.tokens, false)];
		const label = c.name.toLowerCase();
		return [{ id: "other", label, tokens: c.tokens, estimated: false }];
	});
	return merged(rows)
		.filter((r) => r.tokens > 0)
		.sort((a, b) => (BAR_RANK.get(a.id) ?? 0) - (BAR_RANK.get(b.id) ?? 0));
}
