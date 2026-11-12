import type {
	Args,
	EngineInterface,
	Register,
	SessionContextBreakdown,
	SessionContextUsage,
	ToolCallInput,
} from "claude-code";
import { atom, read, update } from "claude-code";

import type { MessageEstimates, UsageModel } from "../types";
import { CATEGORY_STYLES } from "./palette";
import type { GaugeRow } from "./rows";
import { gaugeRows, NO_ESTIMATES } from "./rows";

const usage = atom(
	{ plugin: "context-gauge", key: "usage" } as const,
	null as UsageModel | null,
);

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

/** The spacer on each side of the bar and between a label and its figure; widths count it. */
const SPACE = " ";

function abbrev(n: number): string {
	if (n >= 1_000_000)
		return `${(n / 1_000_000).toFixed(1).replace(/\.0$/u, "")}M`;
	if (n >= 10_000) return `${Math.round(n / 1000)}k`;
	if (n >= 1000) return `${(n / 1000).toFixed(1).replace(/\.0$/u, "")}k`;
	return String(n);
}

function effectiveMax(
	b: SessionContextBreakdown,
	pctRaw: string | undefined,
): number {
	// The breakdown's `autoCompactThreshold` ignores CLAUDE_AUTOCOMPACT_PCT_OVERRIDE,
	// so derive the ceiling from the override the way the settings file states it.
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
function modelFrom(
	context: SessionContextUsage,
	pctRaw: string | undefined,
): UsageModel | null {
	const b = context.breakdown;
	if (!b || b.rawMaxTokens <= 0) return null;
	const max = effectiveMax(b, pctRaw);
	const used = context.tokens ?? b.totalTokens;
	const percent = Math.max(0, Math.min(100, Math.round((used / max) * 100)));
	const scale = b.totalTokens > 0 ? used / b.totalTokens : 1;
	const categories = b.categories
		.filter((c) => c.kind === "used" && c.tokens > 0)
		.map((c) => ({ name: c.name, tokens: Math.round(c.tokens * scale) }));
	return { used, max, percent, categories };
}

async function refresh($: EngineInterface): Promise<void> {
	const [{ context }, pctRaw] = await Promise.all([
		$.session.usage({ breakdown: "summary" }),
		$.env.get("CLAUDE_AUTOCOMPACT_PCT_OVERRIDE"),
	]);
	const model = modelFrom(context, pctRaw);
	await update($, usage, () => model);
}

/** Adds each field's characters to the estimates, in one update. */
async function addChars(
	$: EngineInterface,
	chars: Partial<MessageEstimates>,
): Promise<void> {
	if (!Object.values(chars).some((n) => n > 0)) return;
	await update($, estimates, (e) => ({
		summary: e.summary + (chars.summary ?? 0),
		hooks: e.hooks + (chars.hooks ?? 0),
		attachments: e.attachments + (chars.attachments ?? 0),
		user: e.user + (chars.user ?? 0),
		commands: e.commands + (chars.commands ?? 0),
		deliveries: e.deliveries + (chars.deliveries ?? 0),
		calls: e.calls + (chars.calls ?? 0),
		results: e.results + (chars.results ?? 0),
		read: e.read + (chars.read ?? 0),
		thinking: e.thinking + (chars.thinking ?? 0),
		replies: e.replies + (chars.replies ?? 0),
	}));
}

/** The part of a classic hook result the model reads. */
type HookText = { additionalContext?: readonly string[]; block?: string };

/** Characters a classic hook result hands the model: its context entries and its block reason. */
function hookChars(result: HookText): number {
	const context = (result.additionalContext ?? []).join("").length;
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

/**
 * A classic hook that counts the result's text as hooks text on the main
 * thread; a subagent's hooks fill the subagent's window.
 */
async function countClassic<
	E extends Pick<Args<"classic.Setup">, "agent_id">,
	R extends HookText,
>($: EngineInterface, e: E, next: (e: E) => Promise<R>): Promise<R> {
	const result = await next(e);
	if (e.agent_id === undefined) await addChars($, { hooks: hookChars(result) });
	return result;
}

/** A catch handler that lets the dispatch continue as if the hook were absent. */
function passThrough<E, R>(_$: EngineInterface, e: E, next: (e: E) => R): R {
	return next(e);
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
	const used = rows
		.filter((r) => r.tokens > 0)
		.map((r) => ({
			tokens: r.tokens,
			color: CATEGORY_STYLES[r.id].swatch.hex,
		}));
	const parts = used.concat({
		tokens: Math.max(0, model.max - model.used),
		color: "inactive",
	});
	// One cell set aside for each used row, where every row can have one.
	const rowFloor = used.length <= width ? 1 : 0;
	const shares = largestRemainder(
		parts.map((p) => p.tokens),
		width - rowFloor * used.length,
	);

	const out: Segment[] = [];
	parts.forEach((part, i) => {
		const cells = (shares[i] ?? 0) + (i < used.length ? rowFloor : 0);
		if (cells > 0)
			out.push({ color: part.color, chars: BAR_CELL.repeat(cells) });
	});
	return out;
}

/** A row's legend figure, `~` marking an estimate. */
function figure(row: GaugeRow): string {
	return `${row.estimated ? "~" : ""}${abbrev(row.tokens)}`;
}

/** Cells a legend item takes: its label, a space, its figure. */
function itemCells(row: GaugeRow): number {
	return row.label.length + SPACE.length + figure(row).length;
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
		await addChars($, { hooks: hookChars(result) });
		await refresh($);
		return result;
	}).catch(passThrough);

	// Only a person's own typing counts as user text: task notifications, peers
	// and scheduled triggers enter the window too, and stay in `replies`.
	on("prompt.submit", async ($, e, next) => {
		const result = await next(e);
		const typed = e.origin.kind === "composer" || e.origin.kind === "bridge";
		if (typed && !e.isMeta && result.drop === undefined)
			await addChars($, { user: e.text.length });
		return result;
	}).catch(passThrough);

	// Only main-thread calls count; a subagent's calls and results fill its own window.
	on("tool.call", async ($, e, next) => {
		const result = await next(e);
		if (e.agentId === undefined) {
			const resultField = e.tool === "Read" ? "read" : "results";
			await addChars($, {
				calls: callChars(e),
				[resultField]: (result.deny ?? result.text ?? "").length,
			});
		}
		return result;
	}).catch(passThrough);

	on("classic.Setup", countClassic).catch(passThrough);
	on("classic.UserPromptSubmit", countClassic).catch(passThrough);
	on("classic.UserPromptExpansion", countClassic).catch(passThrough);
	on("classic.PostToolUse", countClassic).catch(passThrough);
	on("classic.PostToolUseFailure", countClassic).catch(passThrough);
	on("classic.PostToolBatch", countClassic).catch(passThrough);
	on("classic.Stop", countClassic).catch(passThrough);
	on("classic.PostModelSwitch", countClassic).catch(passThrough);

	on("ui.render", { component: "PromptHint" }, async ($, e, next) => {
		const [hint, model, chars] = await Promise.all([
			next(e),
			read($, usage),
			read($, estimates),
		]);
		if (model === null) return hint;

		const { Box, Text } = $.ui.resolve(e);
		const rows = gaugeRows(model.categories, chars);
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
			lineCells - percent.length - totals.length - 2 * SPACE.length,
		);

		return (
			<Box flexDirection="column">
				{hint}
				<Box key="gauge">
					<Box flexShrink={0}>
						<Text weight="bold">{percent}</Text>
						<Text>{SPACE}</Text>
					</Box>
					<Box key="bar" flexShrink={1} overflow="hidden" height={1}>
						{barSegments(model, rows, barWidth).map((s, i) => (
							<Text key={`s${i}`} color={s.color}>
								{s.chars}
							</Text>
						))}
					</Box>
					<Box flexShrink={0}>
						<Text>{SPACE}</Text>
						<Text weight="bold">{totals}</Text>
					</Box>
				</Box>
				<Box key="legend" flexDirection="column">
					{lines.map((line, n) => (
						<Box key={`legend-${n}`} columnGap={LEGEND_GAP}>
							{line.rows.map((r) => (
								<Box key={`item-${r.id}-${r.label}`} flexShrink={0}>
									<Text weight="bold" color={CATEGORY_STYLES[r.id].swatch.hex}>
										{r.label}
									</Text>
									<Text>{SPACE}</Text>
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
