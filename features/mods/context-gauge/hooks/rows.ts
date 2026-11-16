/** The gauge's rows: the engine's breakdown rows named, merged and ordered, its Messages row split by the gauge's estimates. */

import type { MessageEstimates, UsageCategory } from "../types";
import type { CountedId } from "./counting";
import type { CategoryId } from "./palette";
import { BAR_ORDER } from "./palette";

const CHARS_PER_TOKEN = 4;

type NamedId = Exclude<CategoryId, "other">;

/** What the legend calls each named category. */
export const LABELS: Readonly<Record<NamedId, string>> = {
	system: "system prompt & tools",
	mcp: "MCP servers",
	agentList: "agent descriptions",
	memory: "memory files",
	skills: "skill list",
	carried: "carried over",
	summary: "compaction summary",
	hooks: "hook output",
	plugins: "plugin context",
	reminders: "Claude Code reminders",
	files: "attached files",
	messages: "messages",
	scripts: "script results",
	tasks: "background tasks",
	relayed: "relayed messages",
	commands: "slash commands",
	calls: "tool calls",
	writes: "file writes",
	results: "tool results",
	read: "file reads",
	prompts: "agent prompts",
	agents: "agent reports",
	thinking: "thinking",
	uncounted: "not yet counted",
	gap: "attribution gap",
};

/** The gauge's category for each breakdown row name the engine reports. */
const ROW_IDS: ReadonlyMap<string, NamedId> = new Map([
	["System prompt", "system"],
	["System tools", "system"],
	["MCP tools", "mcp"],
	["MCP server instructions", "mcp"],
	["Custom agents", "agentList"],
	["Memory files", "memory"],
	["Skills", "skills"],
]);

/** Estimates before anything is counted, and after `/clear` or compaction. */
export const NO_ESTIMATES: MessageEstimates = {
	summary: 0,
	hooks: 0,
	plugins: 0,
	reminders: 0,
	files: 0,
	messages: 0,
	scripts: 0,
	commands: 0,
	calls: 0,
	writes: 0,
	results: 0,
	read: 0,
	prompts: 0,
	agents: 0,
	thinking: 0,
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
	return { id, label: LABELS[id], tokens, estimated };
}

function splitMessages(tokens: number, chars: MessageEstimates): GaugeRow[] {
	const seen =
		COUNTED.reduce((sum, id) => sum + chars[id], 0) / CHARS_PER_TOKEN;
	const scale = seen > tokens ? tokens / seen : 1;
	const counted = COUNTED.map((id) =>
		named(id, Math.round((chars[id] / CHARS_PER_TOKEN) * scale), true),
	);
	const rest = Math.max(0, Math.round(tokens - seen));
	return counted.concat(named("uncounted", rest, false));
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
