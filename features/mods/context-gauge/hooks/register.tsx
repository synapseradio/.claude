/** The context gauge under the prompt: the window's live total and every kind of context in it, drawn as a pixel bar with a character bar where the terminal cannot draw pixels. */

import type {
	ElementTable,
	EngineInterface,
	Hook,
	MatchedHook,
	PluginOptions,
	Register,
	RenderElement,
	SessionAppendInput,
	SessionContextUsage,
	TurnStepResult,
} from "claude-code";
import { atom, read, update } from "claude-code";

import type { MessageEstimates } from "../types";
import { addCounts, rowEffect } from "./counting";
import type { GlyphSet, Run } from "./fallback";
import {
	deniedBeforeMount,
	fallbackRuns,
	glyphSet,
	legendSample,
} from "./fallback";
import type { LegendGrid } from "./layout";
import {
	abbrev,
	barRuns,
	gaugeLine,
	LEGEND_GAP,
	legendGrid,
	PREFIX,
	SAMPLE_CELLS,
	SPACE,
} from "./layout";
import { thinkingTokens, usageModel, windowAfter } from "./live";
import type { BarRun, Theme } from "./palette";
import { PALETTES } from "./palette";
import type { Pixels } from "./pixels";
import { barPixels, PX_PER_CELL, samplePixels } from "./pixels";
import { readCompaction } from "./read-settings";
import { gaugeRows, NO_ESTIMATES } from "./rows";

const context = atom(
	{ plugin: "context-gauge", key: "context" } as const,
	null as SessionContextUsage | null,
);

const compaction = atom(
	{ plugin: "context-gauge", key: "compaction" } as const,
	{ enabled: true, window: null, percent: null },
);

const estimates = atom(
	{ plugin: "context-gauge", key: "estimates" } as const,
	NO_ESTIMATES,
);

const anchor = atom(
	{ plugin: "context-gauge", key: "anchor" } as const,
	null as number | null,
);

const pending = atom({ plugin: "context-gauge", key: "pending" } as const, 0);

const agentCalls = atom(
	{ plugin: "context-gauge", key: "agentCalls" } as const,
	[] as readonly string[],
);

const glyphs = atom(
	{ plugin: "context-gauge", key: "glyphs" } as const,
	null as GlyphSet | null,
);

const theme = atom(
	{ plugin: "context-gauge", key: "theme" } as const,
	"dark" as Theme,
);

/** What the mod's `theme` option asks for: a fixed palette, or Claude Code's own theme. */
type ThemeSetting = Theme | "follow";

/** Reads the mod's `theme` option; a value other than the three reads as dark. */
function themeSetting(options: PluginOptions): ThemeSetting {
	const { theme: asked } = options;
	return asked === "follow" || asked === "light" ? asked : "dark";
}

/** The palette a Claude Code theme name picks: any name starting `light`, else dark. */
function paletteOf(claudeCodeTheme: unknown): Theme {
	return typeof claudeCodeTheme === "string" &&
		claudeCodeTheme.startsWith("light")
		? "light"
		: "dark";
}

/** Reads Claude Code's own `theme` row into the theme atom; a row that cannot be read leaves the last palette. */
async function followClaudeCode($: EngineInterface): Promise<void> {
	const rows = await $.config.list().catch(() => null);
	const row = rows?.find((r) => r.key === "theme");
	if (row === undefined) return;
	await update($, theme, () => paletteOf(row.value));
}

const CHARS_PER_TOKEN = 4;

/** Terminal width when the surface has not measured itself. */
const DEFAULT_COLUMNS = 80;

/**
 * Cells the hint row lacks against `viewport.columns`.
 *
 * Hazard: a line exactly `viewport.columns` cells wide wraps its last three
 * cells onto the next row of the hint.
 */
export const ROW_INSET = 3;

/** The bar Image's key, which its blit names. */
const BAR_KEY = "bar";

/** Whether an event belongs to the main conversation; a subagent's rows, responses and compactions fill the subagent's own window. */
function onMain(e: { readonly agentId?: string | undefined }): boolean {
	return e.agentId === undefined;
}

/** Reads the breakdown and where auto-compaction runs into their atoms; a breakdown that fails to read leaves the last of both. */
async function refresh($: EngineInterface): Promise<void> {
	const [usage, decided] = await Promise.all([
		$.session.usage({ breakdown: "summary" }).catch(() => null),
		readCompaction($),
	]);
	if (usage === null) return;
	await Promise.all([
		update($, context, () => usage.context),
		update($, compaction, () => decided),
	]);
}

/**
 * Counts one kept row into its categories, and into what is pending unless it
 * is a response's own, which its anchor holds; a compaction's row starts the
 * window over from its summary.
 *
 * Hazard: a response's rows are kept before its `turn.step` resolves, so they
 * reach no anchor but their own.
 */
async function countRow(
	$: EngineInterface,
	row: Pick<SessionAppendInput, "door" | "origin" | "message">,
): Promise<void> {
	const effect = rowEffect(row, new Set(await read($, agentCalls)));
	if (effect.agentCalls.length > 0) {
		await update($, agentCalls, (ids) => [...ids, ...effect.agentCalls]);
	}
	if (effect.reset) {
		await resetWindow($, () => addCounts(NO_ESTIMATES, effect.counts), null);
		return;
	}
	if (effect.counts.length === 0) return;
	const chars =
		row.door === "response"
			? 0
			: effect.counts.reduce((sum, c) => sum + c.chars, 0);
	await Promise.all([
		update($, estimates, (e) => addCounts(e, effect.counts)),
		chars > 0 ? update($, pending, (p) => p + chars) : undefined,
	]);
}

/** Anchors the total on a response: the window it left, less pending by the `sent` characters its request carried, its thinking counted, the breakdown read again. */
async function anchorOn(
	$: EngineInterface,
	result: TurnStepResult,
	sent: number,
): Promise<void> {
	if (result.usage === null) return;
	const left = windowAfter(result.usage);
	const thinking = thinkingTokens(result) * CHARS_PER_TOKEN;
	await Promise.all([
		update($, anchor, () => left),
		update($, pending, (p) => p - sent),
		thinking > 0
			? update($, estimates, (e) =>
					addCounts(e, [{ id: "thinking", chars: thinking }]),
				)
			: undefined,
		refresh($),
	]);
}

/** The estimates a compaction leaves: its summary alone, which only its own row sets, so the summary stands whichever of the compaction's signals comes last. */
function compacted(e: MessageEstimates): MessageEstimates {
	return addCounts(NO_ESTIMATES, [{ id: "summary", chars: e.summary }]);
}

/** Starts the window over: the estimates as `estimatesAfter` leaves them, the anchor at `anchorAfter`, nothing pending, the breakdown read again. */
async function resetWindow(
	$: EngineInterface,
	estimatesAfter: (e: MessageEstimates) => MessageEstimates,
	anchorAfter: number | null,
): Promise<void> {
	await Promise.all([
		update($, estimates, estimatesAfter),
		update($, anchor, () => anchorAfter),
		update($, pending, () => 0),
		refresh($),
	]);
}

/** Blits the drawn bar its own source: a denial means the terminal draws the Image's alt, so the bar switches to the glyphs this terminal draws. */
async function checkBar(
	$: EngineInterface,
	requestId: string,
	source: Pixels,
): Promise<void> {
	const blit = await $.ui.blit({ requestId, key: BAR_KEY, source });
	if (blit.deny === undefined || deniedBeforeMount(blit)) return;
	const [termProgram, wtSession] = await Promise.all([
		$.env.get("TERM_PROGRAM"),
		$.env.get("WT_SESSION"),
	]);
	await update($, glyphs, () =>
		glyphSet({ termProgram, wtSession, blitFix: blit.fix }),
	);
}

/** A catch handler that lets the dispatch continue as if the hook were absent. */
function passThrough<E, R>(_$: EngineInterface, e: E, next: (e: E) => R): R {
	return next(e);
}

type Terminal = ElementTable<"terminal">;

/** The bar as an Image of its pixels, one row high. */
function barImage(ui: Terminal, source: Pixels): RenderElement {
	const { Image } = ui;
	return (
		<Image
			key={BAR_KEY}
			source={source}
			columns={source.width / PX_PER_CELL}
			rows={1}
			alt="context bar"
		/>
	);
}

/** The bar as its runs' glyphs, for a terminal where the Image draws its alt. */
function barGlyphs(
	ui: Terminal,
	runs: readonly BarRun[],
	fallback: GlyphSet,
	theme: Theme,
): RenderElement {
	const { Box, Text } = ui;
	return (
		<Box key={BAR_KEY} flexShrink={0}>
			{fallbackRuns(runs, fallback, theme).map((run, i) => (
				<Text key={`run-${i}`} color={run.color}>
					{run.text}
				</Text>
			))}
		</Box>
	);
}

/** A legend key in glyphs: its run's text in its run's colour. */
function glyphKey(ui: Terminal, run: Run): RenderElement {
	const { Text } = ui;
	return <Text color={run.color}>{run.text}</Text>;
}

/** The legend: each line's items, each a unit holding a key, its label in its category's colour and its figure. */
function legend(
	ui: Terminal,
	grid: LegendGrid,
	fallback: GlyphSet | null,
	theme: Theme,
): RenderElement {
	const { Box, Image, Text } = ui;
	return (
		<Box key="legend" flexDirection="column">
			{grid.lines.map((line, n) => (
				<Box key={`legend-${n}`} columnGap={LEGEND_GAP}>
					{line.map(({ row, figure }) => {
						const id = `${row.id}-${row.label}`;
						return (
							<Box key={`item-${id}`} flexShrink={0} width={grid.unit}>
								{fallback === null ? (
									<Image
										key={`key-${id}`}
										source={samplePixels(row.id, SAMPLE_CELLS, theme)}
										columns={SAMPLE_CELLS}
										rows={1}
										alt={SPACE}
									/>
								) : (
									glyphKey(
										ui,
										legendSample(row.id, SAMPLE_CELLS, fallback, theme),
									)
								)}
								<Text>{SPACE}</Text>
								<Text weight="bold" color={PALETTES[theme][row.id].swatch.hex}>
									{row.label}
								</Text>
								<Text>{SPACE}</Text>
								<Text weight="bold">{figure}</Text>
							</Box>
						);
					})}
				</Box>
			))}
		</Box>
	);
}

/** Draws the gauge beneath the engine's hint line on the terminal, and checks once drawn that the bar Image draws. */
const drawGauge: MatchedHook<"ui.render", { component: "PromptHint" }> = async (
	$,
	e,
	next,
) => {
	if (e.surface !== "terminal") return next(e);
	const [
		hint,
		breakdown,
		decided,
		counted,
		anchorTokens,
		pendingChars,
		fallback,
		palette,
	] = await Promise.all([
		next(e),
		read($, context),
		read($, compaction),
		read($, estimates),
		read($, anchor),
		read($, pending),
		read($, glyphs),
		read($, theme),
	]);
	if (breakdown === null) return hint;
	const live = { anchor: anchorTokens, pending: pendingChars };
	const model = usageModel(breakdown, live, decided);
	if (model === null) return hint;

	const ui = $.ui.resolve(e);
	const { Box, Text } = ui;
	const rows = gaugeRows(model.categories, counted);
	const room = (e.viewport?.columns ?? DEFAULT_COLUMNS) - ROW_INSET;
	const percent = `${model.percent}%`;
	const totals = `(${abbrev(model.used)}/${abbrev(model.max)})`;
	const grid = legendGrid(rows, room);
	const prefixCells =
		PREFIX.length +
		percent.length +
		SPACE.length +
		totals.length +
		SPACE.length;
	const shape = gaugeLine(room, prefixCells, rows.length);
	const runs = barRuns(model, rows, shape.cells);
	let barElement: RenderElement | null = null;
	if (fallback !== null) barElement = barGlyphs(ui, runs, fallback, palette);
	else if (runs.length > 0) {
		const source = barPixels(runs, palette);
		$.clock.after(0, () => checkBar($, e.requestId, source));
		barElement = barImage(ui, source);
	}

	return (
		<Box flexDirection="column">
			{hint}
			<Box key="gauge">
				<Box key="label" flexShrink={0}>
					<Text>{PREFIX}</Text>
					<Text weight="bold">{percent}</Text>
					<Text>{SPACE}</Text>
					<Text dimColor={true}>{totals}</Text>
					{shape.barOwnLine ? null : <Text>{SPACE}</Text>}
				</Box>
				{shape.barOwnLine ? null : barElement}
			</Box>
			{shape.barOwnLine ? <Box key="bar-line">{barElement}</Box> : null}
			{legend(ui, grid, fallback, palette)}
		</Box>
	);
};

/** Reads the breakdown as the session starts. */
const refreshOnStart: Hook<"session.start"> = async ($, e, next) => {
	await refresh($);
	return next(e);
};

/** Takes Claude Code's new theme once its `theme` row is written. */
const followThemeChange: MatchedHook<"config.set", { key: "theme" }> = async (
	$,
	e,
	next,
) => {
	const result = await next(e);
	if (result.deny === undefined) {
		await update($, theme, () => paletteOf(result.value));
	}
	return result;
};

/** Counts each row the main conversation keeps, as it is kept. */
const countKept: Hook<"session.append"> = async ($, e, next) => {
	const kept = await next(e);
	if (onMain(e) && kept.message !== undefined) {
		await countRow($, {
			door: e.door,
			origin: e.origin,
			message: kept.message,
		});
	}
	return kept;
};

/** Anchors the total on each main-thread response once it has arrived whole, keeping pending what was appended while its request was in flight. */
const anchorStep: Hook<"turn.step"> = async function* ($, e, next) {
	const sent = onMain(e) ? await read($, pending) : 0;
	const result = yield* next(e);
	if (onMain(e)) await anchorOn($, result, sent);
	return result;
};

/** Starts the window over at its compacted size once a main-thread compaction stands; a precompute changes nothing yet. */
const resetOnCompact: Hook<"session.compact"> = async ($, e, next) => {
	const result = await next(e);
	if (!onMain(e) || e.trigger === "precompute" || result.skip !== undefined) {
		return result;
	}
	await resetWindow($, compacted, result.tokensAfter ?? null);
	return result;
};

/**
 * Starts the window over on `/clear` and after a compaction.
 *
 * Why: `/clear` raises no `session.start`, and the classic SessionStart event
 * carries both as its source, https://code.claude.com/docs/en/hooks#sessionstart
 */
const resetOnStart: Hook<"classic.SessionStart"> = async ($, e, next) => {
	const result = await next(e);
	if (e.source === "clear") await resetWindow($, () => NO_ESTIMATES, null);
	if (e.source === "compact") await resetWindow($, compacted, null);
	return result;
};

/** Registers the gauge: one hook per event it counts, anchors, resets or draws on. */
export const register: Register = (on, options) => {
	const setting = themeSetting(options);
	on("session.start", async ($, e, next) => {
		await (setting === "follow"
			? followClaudeCode($)
			: update($, theme, () => setting));
		return refreshOnStart($, e, next);
	});
	if (setting === "follow") {
		on("config.set", { key: "theme" }, followThemeChange);
	}
	on("session.append", countKept).catch(passThrough);
	on("turn.step", anchorStep);
	on("session.compact", resetOnCompact).catch(passThrough);
	on("classic.SessionStart", resetOnStart).catch(passThrough);
	on("ui.render", { component: "PromptHint" }, drawGauge);
};
