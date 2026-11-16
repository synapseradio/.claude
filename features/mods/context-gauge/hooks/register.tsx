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
	TurnStepInput,
	TurnStepResult,
} from "claude-code";
import { atom, read, update } from "claude-code";

import type { HistoryRead, Ratio, Tally, Window, WindowCause } from "../types";
import { rowPieces } from "./counting";
import type { GlyphSet, Run } from "./fallback";
import {
	deniedBeforeMount,
	fallbackRuns,
	glyphSet,
	legendSample,
} from "./fallback";
import { historyOf } from "./history";
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
import { fixedTokens, usageModel } from "./live";
import type { BarRun, Theme } from "./palette";
import { PALETTES } from "./palette";
import type { Pixels } from "./pixels";
import { barPixels, PX_PER_CELL, samplePixels } from "./pixels";
import { readCompaction } from "./read-settings";
import { gaugeRows } from "./rows";
import {
	applyHistory,
	beginRequest,
	keepRow,
	settleRequest,
	startWindow,
	taint,
} from "./window";

const context = atom(
	{ plugin: "context-gauge", key: "context" } as const,
	null as SessionContextUsage | null,
);

const compaction = atom(
	{ plugin: "context-gauge", key: "compaction" } as const,
	{ enabled: true, window: null, percent: null },
);

const NO_TALLY: Tally = {
	carried: 0,
	summary: 0,
	hooks: 0,
	plugins: 0,
	reminders: 0,
	files: 0,
	messages: 0,
	tasks: 0,
	relayed: 0,
	commands: 0,
	calls: 0,
	writes: 0,
	results: 0,
	read: 0,
	prompts: 0,
	agents: 0,
	thinking: 0,
};

const START: WindowCause = { family: "start", signal: "session.start" };
const UNSEEN: WindowCause = {
	family: "unseen",
	signal: "turn.step:messageCount",
};

/** The window before any signal: a session start whose history is not yet read. */
const FIRST_WINDOW: Window = {
	cause: START,
	measure: { kind: "unmeasured", history: { kind: "unread", why: "not-yet" } },
	open: { chars: NO_TALLY, media: NO_TALLY },
	tainted: false,
	inFlight: null,
	fingerprint: null,
	replaced: null,
};

const window = atom(
	{ plugin: "context-gauge", key: "window" } as const,
	FIRST_WINDOW,
	{ shape: "window-1" },
);

/** No sample yet, so the prior ratio stands. */
const NO_RATIO: Ratio = { model: "", tokens: 0, chars: 0 };

const ratio = atom(
	{ plugin: "context-gauge", key: "ratio" } as const,
	NO_RATIO,
	{
		shape: "ratio-1",
	},
);

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

type Row = Pick<SessionAppendInput, "door" | "origin" | "message">;

/** The model rows and history are measured for, or an empty id where the session names none. */
function modelOf($: EngineInterface): Promise<string> {
	return $.session.model().catch(() => "");
}

/** Joins `found` to the Agent call ids already known, each once. */
async function knowCalls(
	$: EngineInterface,
	found: readonly string[],
): Promise<void> {
	if (found.length === 0) return;
	await update($, agentCalls, (ids) => [...new Set([...ids, ...found])]);
}

/** Reads the main conversation and measures it, its Agent calls known afterwards; a read or a measure that fails reads "failed". */
async function readHistory(
	$: EngineInterface,
): Promise<HistoryRead | "failed"> {
	const model = await modelOf($);
	const history = await $.session
		.messages({ as: "api" })
		.then((messages) => historyOf(messages, model))
		.catch(() => "failed" as const);
	if (history !== "failed") await knowCalls($, history.agentCalls);
	return history;
}

/** Applies a fresh history read to the window. */
async function readInto($: EngineInterface): Promise<void> {
	const history = await readHistory($);
	await update($, window, (w) => applyHistory(w, history));
}

/** Starts the window over on `cause`, under the family merge rule. */
function startOn($: EngineInterface, cause: WindowCause): Promise<void> {
	return update($, window, (w) => startWindow(cause, w)).then(() => undefined);
}

/** Starts the window over on `cause` and reads the breakdown again, and the conversation where the signal leaves it readable. */
async function restart(
	$: EngineInterface,
	cause: WindowCause,
	history: "read" | "unread",
): Promise<void> {
	await startOn($, cause);
	await Promise.all([refresh($), history === "read" ? readInto($) : undefined]);
}

/** The fingerprint of a response row: its first block that is not thinking, as a history read takes it. */
function responseFingerprint(row: Row, model: string): string | null {
	if (row.door !== "response") return null;
	return historyOf([{ role: "assistant", content: row.message.content }], model)
		.fingerprint;
}

/**
 * Keeps one main row in the window: its pieces as input for the next request,
 * or as the output of the response in flight; a response row gives a window
 * without one its fingerprint.
 *
 * Hazard: a response's rows are kept before its `turn.step` resolves, so they
 * reach no anchor but their own.
 */
async function keep($: EngineInterface, row: Row): Promise<void> {
	const [known, model] = await Promise.all([read($, agentCalls), modelOf($)]);
	const pieces = rowPieces(row, new Set(known), model);
	const fingerprint = responseFingerprint(row, model);
	await Promise.all([
		knowCalls($, pieces.agentCalls),
		update($, window, (w) => {
			const kept = keepRow(w, pieces);
			return kept.fingerprint === null && fingerprint !== null
				? { ...kept, fingerprint }
				: kept;
		}),
	]);
}

/** Whether an unmeasured window's history read is unread for `why`. */
function unreadFor(w: Window, why: "not-yet" | "stale"): boolean {
	return (
		w.measure.kind === "unmeasured" &&
		w.measure.history.kind === "unread" &&
		w.measure.history.why === why
	);
}

/** Whether the window must read history at a request's start: its read is stale or not yet made, or a plan-mode exit started it, whose conversation may have swapped since. */
function readsAtRequest(w: Window): boolean {
	if (w.measure.kind === "measured") return false;
	return (
		unreadFor(w, "not-yet") ||
		unreadFor(w, "stale") ||
		w.cause.signal === "session.append:plan_mode_exit" ||
		w.cause.signal === "prompt.attachment:plan_mode_exit"
	);
}

/** The window with the request in flight, or the window as it was where the request carries fewer messages than the last response. */
function begun(w: Window, step: Pick<TurnStepInput, "index" | "messageCount">) {
	const next = beginRequest(w, step);
	return next === "replaced" ? w : next;
}

/** Freezes what a main request carries: a request carrying fewer messages than the last response starts the window over first, and a window that must read history reads it. */
async function beginStep(
	$: EngineInterface,
	step: Pick<TurnStepInput, "index" | "messageCount">,
): Promise<void> {
	const w = await read($, window);
	if (beginRequest(w, step) === "replaced") {
		await restart($, UNSEEN, "read");
	} else if (readsAtRequest(w)) {
		await readInto($);
	}
	await update($, window, (current) => begun(current, step));
}

/** Calibrates the window on a resolved main response against the fixed rows of a breakdown read at that response, and pools its ratio. */
async function settleStep(
	$: EngineInterface,
	result: TurnStepResult,
): Promise<void> {
	await refresh($);
	const [breakdown, pooled] = await Promise.all([
		read($, context),
		read($, ratio),
	]);
	const settled = {
		usage: result.usage,
		fixed:
			breakdown?.breakdown === undefined ? 0 : fixedTokens(breakdown.breakdown),
		served: (result.serverToolUses?.length ?? 0) > 0,
	};
	let ratioAfter = pooled;
	await update($, window, (w) => {
		const next = settleRequest(w, pooled, settled);
		ratioAfter = next.ratio;
		return next.window;
	});
	await update($, ratio, () => ratioAfter);
}

/** Reads what the gauge lacks when it draws with no breakdown or no history read yet, as for a mod enabled mid-session. */
async function catchUp($: EngineInterface, w: Window): Promise<void> {
	await Promise.all([
		refresh($),
		unreadFor(w, "not-yet") ? readInto($) : undefined,
	]);
}

/** Whether a drawing must catch up: no breakdown read, or no history read yet in an unmeasured window. */
function lacksReads(breakdown: SessionContextUsage | null, w: Window): boolean {
	return breakdown === null || unreadFor(w, "not-yet");
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
	const [hint, breakdown, decided, current, pooled, fallback, palette] =
		await Promise.all([
			next(e),
			read($, context),
			read($, compaction),
			read($, window),
			read($, ratio),
			read($, glyphs),
			read($, theme),
		]);
	if (lacksReads(breakdown, current)) {
		$.clock.after(0, () => catchUp($, current));
	}
	if (breakdown === null) return hint;
	const model = usageModel(breakdown, current, pooled, decided);
	if (model === null) return hint;

	const ui = $.ui.resolve(e);
	const { Box, Text } = ui;
	const rows = gaugeRows(model);
	const room = (e.viewport?.columns ?? DEFAULT_COLUMNS) - ROW_INSET;
	const percent = `${model.percent}%`;
	const estimate = model.measured ? "" : "~";
	const totals = `(${estimate}${abbrev(model.used)}/${abbrev(model.max)})`;
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

/** Starts the window as the session starts, with the conversation read; a reload or respawn that finds the conversation the stored window measured keeps it, its interval tainted, since rows kept while hooks were down may be missing. */
async function startSession($: EngineInterface): Promise<void> {
	const [history, stored] = await Promise.all([
		readHistory($),
		read($, window),
	]);
	const reloaded =
		stored.measure.kind === "measured" &&
		history !== "failed" &&
		history.fingerprint !== null &&
		history.fingerprint === stored.fingerprint;
	await Promise.all([
		update($, window, (w) =>
			reloaded ? taint(w) : applyHistory(startWindow(START, w), history),
		),
		refresh($),
	]);
}

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

/** Whether a row has a handler of its own: a compaction's summary, or a plan-mode exit. */
function ownHandler(e: Pick<SessionAppendInput, "door">, row: Row): boolean {
	return e.door === "compaction" || row.message.name === PLAN_MODE_EXIT;
}

/** Keeps each row the main conversation keeps, as it is kept; a compaction's row and a plan-mode exit's are their own handlers'. */
const countKept: Hook<"session.append"> = async ($, e, next) => {
	const kept = await next(e);
	if (!onMain(e) || kept.message === undefined) return kept;
	const row = { door: e.door, origin: e.origin, message: kept.message };
	if (!ownHandler(e, row)) await keep($, row);
	return kept;
};

/** Starts the window over at a compaction's summary row, which then counts as the compaction summary, the conversation it restored read in as carried over. */
const compactOnRow: MatchedHook<
	"session.append",
	{ door: "compaction" }
> = async ($, e, next) => {
	const kept = await next(e);
	if (!onMain(e) || kept.message === undefined) return kept;
	await startOn($, {
		family: "compaction",
		signal: "session.append:compaction",
	});
	await keep($, { door: e.door, origin: e.origin, message: kept.message });
	await Promise.all([refresh($), readInto($)]);
	return kept;
};

/** The attachment a plan-mode exit leaves, by its engine name. */
const PLAN_MODE_EXIT = "plan_mode_exit";

/** Starts the window over once a plan-mode exit's row is kept; the row is in the conversation read as carried over. */
const clearOnExitRow: MatchedHook<
	"session.append",
	{ message: { name: "plan_mode_exit" } }
> = async ($, e, next) => {
	const kept = await next(e);
	if (onMain(e) && kept.message !== undefined) {
		await restart(
			$,
			{ family: "clear", signal: "session.append:plan_mode_exit" },
			"read",
		);
	}
	return kept;
};

/** Starts the window over once a request carries a plan-mode exit's attachment. */
const clearOnExitAttachment: MatchedHook<
	"prompt.attachment",
	{ type: "plan_mode_exit" }
> = async ($, e, next) => {
	const result = await next(e);
	if (onMain(e)) {
		await restart(
			$,
			{ family: "clear", signal: "prompt.attachment:plan_mode_exit" },
			"read",
		);
	}
	return result;
};

/** Records that a main row failed to count, so the next excess shows as attribution gap, and lets the dispatch continue as if the hook were absent. */
async function taintAndPass<E extends { readonly agentId?: string }, R>(
	$: EngineInterface,
	e: E,
	next: (e: E) => R,
): Promise<Awaited<R>> {
	if (onMain(e)) await update($, window, taint);
	return await next(e);
}

/** Calibrates the window on each main-thread response once it has arrived whole; a request carrying fewer messages than the last response starts the window over first. */
const anchorStep: Hook<"turn.step"> = async function* ($, e, next) {
	if (!onMain(e)) return yield* next(e);
	await beginStep($, e);
	const result = yield* next(e);
	await settleStep($, result);
	return result;
};

/** Starts the window over once a main-thread compaction stands; a precompute changes nothing yet. */
const compactOnEvent: Hook<"session.compact"> = async ($, e, next) => {
	const result = await next(e);
	if (!onMain(e) || e.trigger === "precompute" || result.skip !== undefined) {
		return result;
	}
	await restart($, { family: "compaction", signal: "session.compact" }, "read");
	return result;
};

/**
 * The classic SessionStart sources, each starting the window over for its
 * own signal, the conversation read.
 *
 * Why: `/clear` raises no `session.start`, and the classic SessionStart event
 * carries it, https://code.claude.com/docs/en/hooks#sessionstart
 */
const restartOnStartup: MatchedHook<
	"classic.SessionStart",
	{ source: "startup" }
> = async ($, e, next) => {
	const result = await next(e);
	await restart(
		$,
		{ family: "start", signal: "classic.SessionStart:startup" },
		"read",
	);
	return result;
};

const restartOnResume: MatchedHook<
	"classic.SessionStart",
	{ source: "resume" }
> = async ($, e, next) => {
	const result = await next(e);
	await restart(
		$,
		{ family: "resume", signal: "classic.SessionStart:resume" },
		"read",
	);
	return result;
};

const restartOnFork: MatchedHook<
	"classic.SessionStart",
	{ source: "fork" }
> = async ($, e, next) => {
	const result = await next(e);
	await restart(
		$,
		{ family: "resume", signal: "classic.SessionStart:fork" },
		"read",
	);
	return result;
};

const restartOnClear: MatchedHook<
	"classic.SessionStart",
	{ source: "clear" }
> = async ($, e, next) => {
	const result = await next(e);
	await restart(
		$,
		{ family: "clear", signal: "classic.SessionStart:clear" },
		"read",
	);
	return result;
};

const restartOnCompact: MatchedHook<
	"classic.SessionStart",
	{ source: "compact" }
> = async ($, e, next) => {
	const result = await next(e);
	await restart(
		$,
		{ family: "compaction", signal: "classic.SessionStart:compact" },
		"read",
	);
	return result;
};

/** Starts the window over as `/clear` ends the conversation; the new one is read at the next request or drawing. */
const clearOnEnd: MatchedHook<"session.end", { reason: "clear" }> = async (
	$,
	e,
	next,
) => {
	const result = await next(e);
	await restart($, { family: "clear", signal: "session.end:clear" }, "unread");
	return result;
};

/** Starts the window over as a resume ends the conversation; the resumed one is read at the next request or drawing. */
const resumeOnEnd: MatchedHook<"session.end", { reason: "resume" }> = async (
	$,
	e,
	next,
) => {
	const result = await next(e);
	await restart(
		$,
		{ family: "resume", signal: "session.end:resume" },
		"unread",
	);
	return result;
};

/** Registers the gauge: one hook per event it counts, anchors, resets or draws on. */
export const register: Register = (on, options) => {
	const setting = themeSetting(options);
	on("session.start", async ($, e, next) => {
		await (setting === "follow"
			? followClaudeCode($)
			: update($, theme, () => setting));
		await startSession($);
		return next(e);
	});
	if (setting === "follow") {
		on("config.set", { key: "theme" }, followThemeChange);
	}
	on("session.append", countKept).catch(taintAndPass);
	on("session.append", { door: "compaction" }, compactOnRow).catch(
		taintAndPass,
	);
	on(
		"session.append",
		{ message: { name: PLAN_MODE_EXIT } },
		clearOnExitRow,
	).catch(passThrough);
	on(
		"prompt.attachment",
		{ type: PLAN_MODE_EXIT },
		clearOnExitAttachment,
	).catch(passThrough);
	on("turn.step", anchorStep);
	on("session.compact", compactOnEvent).catch(passThrough);
	on("classic.SessionStart", { source: "startup" }, restartOnStartup).catch(
		passThrough,
	);
	on("classic.SessionStart", { source: "resume" }, restartOnResume).catch(
		passThrough,
	);
	on("classic.SessionStart", { source: "fork" }, restartOnFork).catch(
		passThrough,
	);
	on("classic.SessionStart", { source: "clear" }, restartOnClear).catch(
		passThrough,
	);
	on("classic.SessionStart", { source: "compact" }, restartOnCompact).catch(
		passThrough,
	);
	on("session.end", { reason: "clear" }, clearOnEnd).catch(passThrough);
	on("session.end", { reason: "resume" }, resumeOnEnd).catch(passThrough);
	on("ui.render", { component: "PromptHint" }, drawGauge);
};
