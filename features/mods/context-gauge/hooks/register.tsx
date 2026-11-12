import type {
	EngineInterface,
	Register,
	SessionContextBreakdown,
	SessionContextUsage,
	ToolCallInput,
} from "claude-code";
import { atom, read, update } from "claude-code";

import type { MessageEstimates, UsageModel } from "../types";
import { CATEGORY_SWATCHES, fillSwatch } from "./palette";
import type { GaugeRow } from "./rows";
import { gaugeRows } from "./rows";

const usage = atom(
	{ plugin: "context-gauge", key: "usage" } as const,
	null as UsageModel | null,
);

const NO_ESTIMATES: MessageEstimates = {
	hooks: 0,
	user: 0,
	calls: 0,
	results: 0,
	read: 0,
};
const estimates = atom(
	{ plugin: "context-gauge", key: "estimates" } as const,
	NO_ESTIMATES,
);

/** Terminal width when the surface has not measured itself. */
const DEFAULT_COLUMNS = 80;
/**
 * Cells the terminal's hint row lacks against `viewport.columns`: a bar line
 * exactly `columns` wide wrapped three cells onto the next row.
 */
const ROW_INSET = 3;
const MIN_BAR_CELLS = 10;

/**
 * Every bar cell, used and free: the sextant filling a cell's middle third
 * (U+1FB0B), so the bar sits centred on the text line with space above and
 * below it.
 */
const BAR_CELL = "\u{1FB0B}";

/** Cells between legend items. */
const LEGEND_GAP = 2;

function abbrev(n: number): string {
	if (n >= 1_000_000)
		return `${(n / 1_000_000).toFixed(1).replace(/\.0$/u, "")}M`;
	if (n >= 10_000) return `${Math.round(n / 1000)}k`;
	if (n >= 1000) return `${(n / 1000).toFixed(1).replace(/\.0$/u, "")}k`;
	return String(n);
}

async function effectiveMax(
	$: EngineInterface,
	b: SessionContextBreakdown,
): Promise<number> {
	// The breakdown's `autoCompactThreshold` ignores CLAUDE_AUTOCOMPACT_PCT_OVERRIDE,
	// so derive the ceiling from the override the way the settings file states it.
	const pctRaw = await $.env.get("CLAUDE_AUTOCOMPACT_PCT_OVERRIDE");
	const pct = pctRaw ? Number(pctRaw) : Number.NaN;
	if (Number.isFinite(pct) && pct > 0 && pct <= 100) {
		return Math.floor((b.rawMaxTokens * pct) / 100);
	}
	return b.autoCompactThreshold ?? b.rawMaxTokens;
}

/**
 * Counts `used` from the last API response's input tokens, the figure the
 * status line shows, and falls back to the breakdown's local estimate until a
 * response arrives in a fresh, cleared, or compacted window. Category figures
 * are scaled so they sum to `used`.
 */
async function modelFrom(
	$: EngineInterface,
	context: SessionContextUsage,
): Promise<UsageModel | null> {
	const b = context.breakdown;
	if (!b || b.rawMaxTokens <= 0) return null;
	const max = await effectiveMax($, b);
	const used = context.tokens ?? b.totalTokens;
	const percent = Math.max(0, Math.min(100, Math.round((used / max) * 100)));
	const scale = b.totalTokens > 0 ? used / b.totalTokens : 1;
	const categories = b.categories
		.filter((c) => c.kind === "used" && c.tokens > 0)
		.map((c) => ({ name: c.name, tokens: Math.round(c.tokens * scale) }));
	return { used, max, percent, categories };
}

async function refresh($: EngineInterface): Promise<void> {
	const { context } = await $.session.usage({ breakdown: "summary" });
	const model = await modelFrom($, context);
	await update($, usage, () => model);
}

async function count(
	$: EngineInterface,
	field: keyof MessageEstimates,
	chars: number,
): Promise<void> {
	if (chars > 0)
		await update($, estimates, (e) => ({ ...e, [field]: e[field] + chars }));
}

/** Characters a classic hook result hands the model: its context entries and its block reason. */
function hookChars(result: {
	additionalContext?: readonly string[];
	block?: string;
}): number {
	const context = (result.additionalContext ?? []).reduce(
		(sum, text) => sum + text.length,
		0,
	);
	return context + (result.block?.length ?? 0);
}

/** The keys `tool.call`'s input carries that the tool never sees. */
const RESERVED_INPUT_KEYS = new Set([
	"tool",
	"tool_use_id",
	"consent",
	"agentId",
	"requestMeta",
]);

/** Characters a tool call hands the model: the tool's name and its arguments as JSON. */
function callChars(e: ToolCallInput): number {
	const args = Object.fromEntries(
		Object.entries(e).filter(([key]) => !RESERVED_INPUT_KEYS.has(key)),
	);
	return e.tool.length + JSON.stringify(args).length;
}

/** Counts a main-thread hook result; a subagent's hooks fill the subagent's window. */
async function countHooks<
	R extends { additionalContext?: readonly string[]; block?: string },
>($: EngineInterface, fromSubagent: boolean, result: R): Promise<R> {
	if (!fromSubagent) await count($, "hooks", hookChars(result));
	return result;
}

/**
 * Splits `cells` across `weights` in proportion, by largest remainder, so the
 * counts sum to `cells` exactly.
 */
function largestRemainder(weights: readonly number[], cells: number): number[] {
	const total = weights.reduce((a, b) => a + b, 0);
	if (total <= 0 || cells <= 0) return weights.map(() => 0);
	const raw = weights.map((w) => (w / total) * cells);
	const counts = raw.map((r) => Math.floor(r));
	const leftover = cells - counts.reduce((a, b) => a + b, 0);
	const order = raw
		.map((_, i) => i)
		.sort((a, b) => ((raw[b] ?? 0) % 1) - ((raw[a] ?? 0) % 1));
	for (const i of order.slice(0, leftover)) counts[i] = (counts[i] ?? 0) + 1;
	return counts;
}

type Segment = { color: string; chars: string };

/**
 * The bar, `width` cells: each row with tokens owns at least one cell in its
 * colour, the remaining cells split by tokens against the window, and free
 * space fills the rest in the inactive colour. Where rows outnumber cells,
 * every part takes its plain proportional share.
 */
function barSegments(
	model: UsageModel,
	rows: readonly GaugeRow[],
	width: number,
): Segment[] {
	const parts = [
		...rows
			.filter((r) => r.tokens > 0)
			.map((r) => ({
				tokens: r.tokens,
				color: CATEGORY_SWATCHES[r.id].hex,
				floor: 1,
			})),
		{
			tokens: Math.max(0, model.max - model.used),
			color: "inactive",
			floor: 0,
		},
	];
	const floors = parts.map((p) => p.floor);
	const reserved = floors.reduce((a, b) => a + b, 0);
	const seeded = reserved <= width;
	const shares = largestRemainder(
		parts.map((p) => p.tokens),
		seeded ? width - reserved : width,
	);

	const out: Segment[] = [];
	parts.forEach((part, i) => {
		const cells = (shares[i] ?? 0) + (seeded ? (floors[i] ?? 0) : 0);
		if (cells > 0)
			out.push({ color: part.color, chars: BAR_CELL.repeat(cells) });
	});
	return out;
}

/** A row's legend figure, `~` marking an estimate. */
function figure(row: GaugeRow): string {
	return `${row.estimated ? "~" : ""}${abbrev(row.tokens)}`;
}

/** Cells a legend item takes: its label, one space, its figure. */
function itemCells(row: GaugeRow): number {
	return row.label.length + 1 + figure(row).length;
}

type LegendLine = { rows: GaugeRow[]; cells: number };

/**
 * Legend rows in lines, each item at its own width and `LEGEND_GAP` cells
 * apart, a line breaking where its next item would pass `room` cells.
 */
function legendLines(rows: readonly GaugeRow[], room: number): LegendLine[] {
	const lines: LegendLine[] = [];
	for (const row of rows) {
		const line = lines.at(-1);
		const needed = itemCells(row);
		if (line !== undefined && line.cells + LEGEND_GAP + needed <= room) {
			line.rows.push(row);
			line.cells += LEGEND_GAP + needed;
		} else {
			lines.push({ rows: [row], cells: needed });
		}
	}
	return lines;
}

export const register: Register = (on) => {
	on("session.start", async ($, e, next) => {
		await refresh($);
		return next(e);
	});

	on("session.measure", async ($, e, next) => {
		await refresh($);
		return next(e);
	});

	// `/clear` ends the session without a `session.start` for the new one, and
	// compaction replaces the messages the estimates counted; the classic
	// SessionStart event carries both as its `source`.
	on("classic.SessionStart", async ($, e, next) => {
		if (e.source === "clear" || e.source === "compact")
			await update($, estimates, () => NO_ESTIMATES);
		const result = await next(e);
		await count($, "hooks", hookChars(result));
		await refresh($);
		return result;
	}).catch((_$, e, next) => next(e));

	// Only a person's own typing counts as user text: task notifications, peers
	// and scheduled triggers enter the window too, and stay in `replies`.
	on("prompt.submit", async ($, e, next) => {
		const result = await next(e);
		const typed = e.origin.kind === "composer" || e.origin.kind === "bridge";
		if (typed && !e.isMeta && result.drop === undefined)
			await count($, "user", e.text.length);
		return result;
	}).catch((_$, e, next) => next(e));

	// Only main-thread calls count; a subagent's calls and results fill its own window.
	on("tool.call", async ($, e, next) => {
		const result = await next(e);
		if (e.agentId === undefined) {
			await count($, "calls", callChars(e));
			await count(
				$,
				e.tool === "Read" ? "read" : "results",
				(result.deny ?? result.text ?? "").length,
			);
		}
		return result;
	}).catch((_$, e, next) => next(e));

	on("classic.Setup", async ($, e, next) =>
		countHooks($, e.agent_id !== undefined, await next(e)),
	).catch((_$, e, next) => next(e));
	on("classic.UserPromptSubmit", async ($, e, next) =>
		countHooks($, e.agent_id !== undefined, await next(e)),
	).catch((_$, e, next) => next(e));
	on("classic.UserPromptExpansion", async ($, e, next) =>
		countHooks($, e.agent_id !== undefined, await next(e)),
	).catch((_$, e, next) => next(e));
	on("classic.PostToolUse", async ($, e, next) =>
		countHooks($, e.agent_id !== undefined, await next(e)),
	).catch((_$, e, next) => next(e));
	on("classic.PostToolUseFailure", async ($, e, next) =>
		countHooks($, e.agent_id !== undefined, await next(e)),
	).catch((_$, e, next) => next(e));
	on("classic.PostToolBatch", async ($, e, next) =>
		countHooks($, e.agent_id !== undefined, await next(e)),
	).catch((_$, e, next) => next(e));
	on("classic.Stop", async ($, e, next) =>
		countHooks($, e.agent_id !== undefined, await next(e)),
	).catch((_$, e, next) => next(e));
	on("classic.PostModelSwitch", async ($, e, next) =>
		countHooks($, e.agent_id !== undefined, await next(e)),
	).catch((_$, e, next) => next(e));

	on("ui.render", { component: "PromptHint" }, async ($, e, next) => {
		const model = await read($, usage);
		if (model === null) return next(e);

		const { Box, Text } = $.ui.resolve(e);
		const rows = gaugeRows(model.categories, await read($, estimates));
		const width = e.viewport?.columns ?? DEFAULT_COLUMNS;
		const percent = `${model.percent}%`;
		const totals = `${abbrev(model.used)}/${abbrev(model.max)}`;
		const lines = legendLines(rows, width - ROW_INSET);
		// The bar line ends where the widest legend line ends.
		const lineCells = lines.reduce(
			(widest, line) => Math.max(widest, line.cells),
			0,
		);
		const barWidth = Math.max(
			MIN_BAR_CELLS,
			lineCells - percent.length - totals.length - 2,
		);

		return (
			<Box flexDirection="column">
				{await next(e)}
				<Box key="gauge">
					<Box flexShrink={0}>
						<Text weight="bold" color={fillSwatch(model.percent).hex}>
							{percent}
						</Text>
						<Text> </Text>
					</Box>
					<Box key="bar" flexShrink={1} overflow="hidden" height={1}>
						{barSegments(model, rows, barWidth).map((s, i) => (
							<Text key={`s${i}`} color={s.color}>
								{s.chars}
							</Text>
						))}
					</Box>
					<Box flexShrink={0}>
						<Text> </Text>
						<Text weight="bold">{totals}</Text>
					</Box>
				</Box>
				<Box key="legend" flexDirection="column">
					{lines.map((line, n) => (
						<Box key={`legend-${n}`} columnGap={LEGEND_GAP}>
							{line.rows.map((r) => (
								<Box key={`item-${r.id}-${r.label}`} flexShrink={0}>
									<Text weight="bold" color={CATEGORY_SWATCHES[r.id].hex}>
										{r.label}
									</Text>
									<Text> </Text>
									<Text weight="bold">{figure(r)}</Text>
								</Box>
							))}
						</Box>
					))}
				</Box>
			</Box>
		);
	});
};
