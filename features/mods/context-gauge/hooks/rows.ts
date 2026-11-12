/** The gauge's rows: the engine's breakdown rows named, merged and ordered, its Messages row split by the gauge's estimates. */

import type { MessageEstimates, UsageCategory } from "../types";
import type { CategoryId } from "./palette";
import { CATEGORY_SWATCHES } from "./palette";

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

/** The Messages row's estimated parts, in bar order. */
const ESTIMATED: readonly (keyof MessageEstimates & NamedId)[] = [
	"hooks",
	"user",
	"calls",
	"results",
	"read",
];

/** Estimates before anything is counted, and after `/clear` or compaction. */
export const NO_ESTIMATES: MessageEstimates = {
	hooks: 0,
	user: 0,
	calls: 0,
	results: 0,
	read: 0,
};

/** Each category's place in the bar, the swatch table's key order. */
const BAR_RANK: ReadonlyMap<string, number> = new Map(
	Object.keys(CATEGORY_SWATCHES).map((id, rank) => [id, rank]),
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

/** Splits the Messages row's tokens into the estimated rows and the remainder. */
function splitMessages(tokens: number, chars: MessageEstimates): GaugeRow[] {
	const seen =
		ESTIMATED.reduce((sum, id) => sum + chars[id], 0) / CHARS_PER_TOKEN;
	const scale = seen > tokens ? tokens / seen : 1;
	const estimated = ESTIMATED.map((id) =>
		named(id, Math.round((chars[id] / CHARS_PER_TOKEN) * scale), true),
	);
	const rest = tokens - estimated.reduce((sum, r) => sum + r.tokens, 0);
	return estimated.concat(named("replies", Math.max(0, rest), false));
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
