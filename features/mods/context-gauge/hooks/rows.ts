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

const LABELS: Readonly<Record<NamedId, string>> = {
	system: "system",
	mcp: "mcp",
	agents: "agents",
	memory: "memory",
	skills: "skills",
	hooks: "hooks",
	user: "user",
	calls: "calls",
	results: "results",
	read: "read",
	replies: "replies",
};

/** The Messages row's estimated parts, in bar order. */
const ESTIMATED: readonly (keyof MessageEstimates & NamedId)[] = [
	"hooks",
	"user",
	"calls",
	"results",
	"read",
];

const BAR_ORDER = Object.keys(CATEGORY_SWATCHES) as CategoryId[];

export type GaugeRow = {
	id: CategoryId;
	label: string;
	tokens: number;
	estimated: boolean;
};

function named(id: NamedId, tokens: number, estimated: boolean): GaugeRow {
	return { id, label: LABELS[id], tokens, estimated };
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
	return [...estimated, named("replies", Math.max(0, rest), false)];
}

/** Sums the tokens of rows sharing an id and label, keeping the first one's place. */
function merged(rows: readonly GaugeRow[]): GaugeRow[] {
	const byKey = new Map<string, GaugeRow>();
	for (const r of rows) {
		const key = `${r.id}\u0000${r.label}`;
		const seen = byKey.get(key);
		byKey.set(key, seen ? { ...seen, tokens: seen.tokens + r.tokens } : r);
	}
	return [...byKey.values()];
}

/** The rows the gauge draws, in bar order, each with tokens. */
export function gaugeRows(
	categories: readonly UsageCategory[],
	chars: MessageEstimates,
): GaugeRow[] {
	const rows = categories.flatMap((c): GaugeRow[] => {
		if (c.name === "Messages") return splitMessages(c.tokens, chars);
		const id = ROW_IDS.get(c.name);
		return [
			id
				? named(id, c.tokens, false)
				: {
						id: "other",
						label: c.name.toLowerCase(),
						tokens: c.tokens,
						estimated: false,
					},
		];
	});
	return merged(rows)
		.filter((r) => r.tokens > 0)
		.sort((a, b) => BAR_ORDER.indexOf(a.id) - BAR_ORDER.indexOf(b.id));
}
