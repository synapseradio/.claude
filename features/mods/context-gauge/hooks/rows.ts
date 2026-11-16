/** The gauge's rows: the engine's fixed breakdown rows named, merged and ordered, beside the calibrated message categories and the attribution gap. */

import type { CountedId, UsageModel } from "../types";
import { GAP_FLOOR_SHARE, GAP_FLOOR_TOKENS } from "./calibration";
import type { CategoryId } from "./palette";
import { BAR_ORDER } from "./palette";

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

function fixedRow(c: UsageModel["fixed"][number]): GaugeRow {
	const id = ROW_IDS.get(c.name);
	if (id) return named(id, c.tokens, false);
	return {
		id: "other",
		label: c.name.toLowerCase(),
		tokens: c.tokens,
		estimated: false,
	};
}

/** Whether the attribution gap is large enough to draw: at least GAP_FLOOR_TOKENS, and at least GAP_FLOOR_SHARE of the window's message tokens, the gap among them. */
function gapShows(gap: number, messageTokens: number): boolean {
	return gap >= Math.max(GAP_FLOOR_TOKENS, GAP_FLOOR_SHARE * messageTokens);
}

/** The rows the gauge draws, in bar order, each with whole tokens: the engine's fixed rows as reported, each message category estimated, and the attribution gap where it shows. */
export function gaugeRows(
	model: Pick<UsageModel, "fixed" | "messages" | "gap">,
): GaugeRow[] {
	const ids = Object.keys(model.messages) as CountedId[];
	const messageTokens = ids.reduce(
		(sum, id) => sum + model.messages[id],
		model.gap,
	);
	const rows = model.fixed
		.map(fixedRow)
		.concat(ids.map((id) => named(id, model.messages[id], true)))
		.concat(
			gapShows(model.gap, messageTokens)
				? [named("gap", model.gap, false)]
				: [],
		);
	return merged(rows)
		.map((r) => ({ ...r, tokens: Math.round(r.tokens) }))
		.filter((r) => r.tokens > 0)
		.sort((a, b) => (BAR_RANK.get(a.id) ?? 0) - (BAR_RANK.get(b.id) ?? 0));
}
