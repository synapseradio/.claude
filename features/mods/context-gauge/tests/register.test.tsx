import type {
	ApiContentBlock,
	ContextCategory,
	HookStream,
	On,
	SessionAppendInput,
	SessionCompactResult,
	SessionMessage,
	SessionUsage,
	Settings,
	SettingsSource,
	TurnUsage,
	UiBlitResult,
} from "claude-code";
import type {
	Engine,
	FoundElement,
	MockClock,
	MockSession,
} from "claude-code/testing";
import { describe, expect, mock, test } from "claude-code/testing";

import { FREE_GLYPH, legendSample, TEXTURE_GLYPHS } from "../hooks/fallback";
import { LEGEND_GAP, SAMPLE_CELLS, SPACE } from "../hooks/layout";
import { CATEGORY_STYLES } from "../hooks/palette";
import { PX_HEIGHT, PX_PER_CELL, samplePixels } from "../hooks/pixels";
import { ROW_INSET } from "../hooks/register";

/** The widest Image source the engine takes, in pixels (ImageSource's `width`). */
const IMAGE_MAX_PX = 2048;

/** Cells a drawn string takes: one per code point, the bar's astral glyphs included. */
function cells(text: string): number {
	return text.match(/./gsu)?.length ?? 0;
}

const HINT = {
	plugin: "context-gauge",
	component: "PromptHint",
	surface: "terminal",
	props: {
		isDraft: false,
		isWorking: false,
		hint: "⏵⏵ accept edits on (shift+tab to cycle)",
	},
} as const;

const VIEWPORT = { columns: 80, rows: 24 } as const;

type Viewport = { columns: number; rows: number };

/** Mounts the hint line `viewport` cells across. */
function mount($: Engine, viewport: Viewport = VIEWPORT) {
	return $.ui.mount({
		plugin: HINT.plugin,
		component: HINT.component,
		surface: HINT.surface,
		props: HINT.props,
		viewport,
	});
}

/** The widest of `widths`, 0 for none. */
function widestOf(widths: readonly number[]): number {
	return widths.reduce((widest, w) => Math.max(widest, w), 0);
}

const ICONS = /[○◔◑◕●⊞⚙⇄◇▤✦✉]/u;

function row(
	name: string,
	tokens: number,
	kind: ContextCategory["kind"] = "used",
): ContextCategory {
	return { name, tokens, color: "inactive", isDeferred: false, kind };
}

/** The breakdown rows of a window holding 30,000 of 100,000 tokens, 20,000 of them messages. */
const ROWS: readonly ContextCategory[] = [
	row("System prompt", 6000),
	row("Skills", 4000),
	row("Messages", 20_000),
];

/** A session's usage whose breakdown holds `rows` in a window of `window` tokens, 100,000 unless given. */
function usageOf(
	rows: readonly ContextCategory[],
	window = 100_000,
): SessionUsage {
	const total = rows.reduce((sum, r) => sum + r.tokens, 0);
	return {
		startedAt: 0,
		rateLimits: [],
		context: {
			tokens: total,
			window,
			breakdown: {
				categories: rows.concat(row("Free space", window - total, "free")),
				totalTokens: total,
				maxTokens: window,
				rawMaxTokens: window,
				autocompactSource: "model-default",
				percentage: Math.round((total / window) * 100),
				gridRows: [],
				model: "test",
				memoryFiles: [],
				mcpTools: [],
				agents: [],
				isAutoCompactEnabled: false,
				apiUsage: null,
			},
		},
	};
}

type Fixture = {
	rows?: readonly ContextCategory[];
	/** The window the breakdown measures against, in tokens; 100,000 by default. */
	window?: number;
	/** TERM_PROGRAM, the terminal the session runs in; unset by default. */
	termProgram?: string;
	/** The environment variables the session runs with, besides TERM_PROGRAM; none by default. */
	variables?: readonly (readonly [name: string, value: string])[];
	/** What each settings source holds; a source left out reads as empty. Read at each read, so a test may change it. */
	sources?: Partial<Record<SettingsSource, Settings>>;
	/** Makes every settings read reject. */
	settingsFail?: boolean;
	/** The session's model id; none by default, so a read of it rejects. */
	model?: string;
	/** Each `$.session.usage` call's answer, by call number from 0. */
	usage?: (call: number) => SessionUsage;
	/** What every blit on the bar Image answers; by default, that it drew. */
	blit?: UiBlitResult;
};

type World = { session: MockSession; clock: MockClock };

// Stands for the engine beneath the plugin: by default a session whose window
// holds 30,000 of 100,000 tokens, 20,000 of them messages, on a terminal that
// draws Images.
function engine(on: On, fixture: Fixture = {}): World {
	const usage =
		fixture.usage ?? (() => usageOf(fixture.rows ?? ROWS, fixture.window));
	const blit = fixture.blit ?? {};
	let calls = 0;
	const terminal =
		fixture.termProgram === undefined
			? []
			: [["TERM_PROGRAM", fixture.termProgram]];
	mock.env(on, Object.fromEntries([...terminal, ...(fixture.variables ?? [])]));
	on("settings.read", (_, e) => {
		if (fixture.settingsFail === true) return { deny: "unreadable" };
		const source =
			e.source === undefined ? undefined : fixture.sources?.[e.source];
		return { value: source ?? {} };
	});
	const { model } = fixture;
	if (model !== undefined) on("session.model", () => ({ value: model }));
	const clock = mock.clock(on);
	const session = mock.session(on);
	on("session.start", (_, e) => ({ cwd: e.cwd }));
	on("classic.SessionStart", () => ({}));
	on("session.usage", () => ({ value: usage(calls++) }));
	on("ui.blit", () => ({ value: blit }));
	on("ui.render", ($, e) => {
		const { Text } = $.ui.resolve(e);
		return <Text>engine hint line</Text>;
	});
	return { session, clock };
}

/** Starts an interactive terminal session, the one every test draws in. */
async function startSession($: Engine): Promise<void> {
	await $.session.start({ cwd: "/", surface: "terminal", isInteractive: true });
}

function text(chars: number): ApiContentBlock {
	return { type: "text", text: "x".repeat(chars) };
}

type Door = SessionAppendInput["door"];
type Origin = SessionAppendInput["origin"];

let rowNumber = 0;

/** Appends one user-side row of `chars` characters through `door`, from `origin`. */
async function append(
	$: Engine,
	door: Door,
	origin: Origin,
	chars: number,
	agentId?: string,
): Promise<void> {
	const input: SessionAppendInput = {
		door,
		origin,
		uuid: `row-${rowNumber++}`,
		message: { type: "user", role: "user", content: [text(chars)] },
	};
	if (agentId !== undefined) input.agentId = agentId;
	await $.session.append(input);
}

const TYPED: Origin = { kind: "composer" };
const READ: Origin = { kind: "tool", tool: "Read" };
const BASH: Origin = { kind: "tool", tool: "Bash" };
const ENGINE: Origin = { kind: "engine" };

/** A model response's usage: what it read, cached and wrote. */
function usage(input: number, cacheRead: number, output: number): TurnUsage {
	return {
		model: "test",
		input_tokens: input,
		cache_read_input_tokens: cacheRead,
		cache_creation_input_tokens: 0,
		output_tokens: output,
	};
}

type Reply = { answer?: string; arrived?: Promise<void> };

/** Answers every model request with its answer as one text chunk, at `spent`, once `arrived` settles. */
function respond(on: On, spent: TurnUsage, reply: Reply = {}): void {
	const answer = reply.answer ?? "";
	on("turn.step", async function* (_, e) {
		yield { kind: "text", index: 0, text: answer };
		await reply.arrived;
		return {
			turnId: e.turnId,
			index: e.index,
			answer,
			toolUses: [],
			stopReason: "end_turn",
			usage: spent,
		};
	});
}

/** Reads a stream to its end and resolves what it returned. */
async function drain<C, R>(stream: HookStream<C, R>): Promise<R> {
	let step = await stream.next();
	while (step.done !== true) step = await stream.next();
	return step.value;
}

/** Runs one model request of the main conversation, or of subagent `agentId`. */
async function step($: Engine, agentId?: string): Promise<void> {
	const input: Parameters<Engine["turn"]["step"]>[0] = {
		turnId: "turn",
		index: 0,
		model: "test",
		messageCount: 1,
	};
	if (agentId !== undefined) input.agentId = agentId;
	await drain($.turn.step(input));
}

/** Answers every compaction with a summary and `tokensAfter` tokens left, or skips it. */
function compactTo(on: On, tokensAfter: number | "skip"): void {
	const summary: SessionMessage = {
		role: "user",
		text: "summary",
		toolUses: [],
	};
	on(
		"session.compact",
		(): SessionCompactResult =>
			tokensAfter === "skip"
				? { skip: "off" }
				: { messages: [summary], tokensAfter },
	);
}

type Trigger = Parameters<Engine["session"]["compact"]>[0]["trigger"];

/** Compacts a one-message conversation, the main one or subagent `agentId`'s. */
async function compact(
	$: Engine,
	trigger: Trigger,
	agentId?: string,
): Promise<void> {
	const input: Parameters<Engine["session"]["compact"]>[0] = {
		trigger,
		messages: [{ role: "user", text: "hi", toolUses: [] }],
	};
	if (agentId !== undefined) input.agentId = agentId;
	await $.session.compact(input);
}

type Drawn = {
	gauge: FoundElement | undefined;
	bar: FoundElement | undefined;
	totals: FoundElement | undefined;
	legend: string;
	lines: FoundElement[];
	images: FoundElement[];
	texts: FoundElement[];
};

/** Everything a test reads off one drawing at `viewport`, mounted and unmounted around the reads. */
async function drawn($: Engine, viewport: Viewport = VIEWPORT): Promise<Drawn> {
	const ui = await mount($, viewport);
	const gauge = await ui.find({ key: "gauge" });
	const bar = await ui.find({ key: "bar" });
	const totals = await ui.find({ key: "totals" });
	const legend = (await ui.find({ key: "legend" }))?.text ?? "";
	const lines: FoundElement[] = [];
	for (let n = 0; ; n++) {
		const line = await ui.find({ key: `legend-${n}` });
		if (line === undefined) break;
		lines.push(line);
	}
	const images = await ui.findAll({ type: "Image" });
	const texts = await ui.findAll({ type: "Text" });
	await ui.unmount();
	return { gauge, bar, totals, legend, lines, images, texts };
}

/** The props the gauge's tests read off a drawn element. */
type DrawnProps = {
	color?: unknown;
	backgroundColor?: unknown;
	weight?: unknown;
	columnGap?: unknown;
	columns?: unknown;
	rows?: unknown;
	source?: unknown;
};

/** The props the tests read off a drawn element, none where the element is absent. */
function propsOf(node: { props: DrawnProps } | undefined): DrawnProps {
	return node?.props ?? {};
}

/** A drawn Image's columns, or a drawn character bar's cells. */
function barWidth(bar: FoundElement | undefined): number {
	if (bar?.type === "Image") return Number(propsOf(bar).columns);
	return cells(bar?.text ?? "");
}

/** Cells the bar line takes: the percentage, a space, the bar, and the totals with their space where they stay on it. */
function gaugeCells(d: Drawn): number {
	const percent = d.texts.find((t) => /^\d+%$/u.test(t.text))?.text ?? "";
	const totals =
		d.totals === undefined
			? (/\d+k\/\d+k$/u.exec(d.gauge?.text ?? "")?.[0] ?? "")
			: "";
	const tail = totals === "" ? 0 : SPACE.length + totals.length;
	return percent.length + SPACE.length + barWidth(d.bar) + tail;
}

/** Cells a legend line takes: each item's key and its text, and the gaps between items. */
function lineCells(line: FoundElement): number {
	const items = line.children.length;
	return cells(line.text) + items * SAMPLE_CELLS + LEGEND_GAP * (items - 1);
}

function legendText($: Engine): Promise<string> {
	return drawn($).then((d) => d.legend);
}

function gaugeText($: Engine): Promise<string> {
	return drawn($).then((d) => d.gauge?.text ?? "");
}

describe("the gauge under the prompt", () => {
	test("sits on its own line beneath the engine hint line, percentage first, no icons", async ($, on) => {
		engine(on);
		await startSession($);

		const d = await drawn($);

		expect(d.texts[0]?.text).toBe("engine hint line");
		expect(d.gauge?.text.trimStart().startsWith("30%")).toBe(true);
		expect(ICONS.test(d.texts.map((t) => t.text).join(""))).toBe(false);
	});

	test("each category label is bold in its swatch colour, with no background", async ($, on) => {
		engine(on);
		await startSession($);

		const label = (await drawn($)).texts.find((t) => t.text === "system");

		expect(propsOf(label).color).toBe(CATEGORY_STYLES.system.swatch.hex);
		expect(propsOf(label).backgroundColor).toBeUndefined();
		expect(propsOf(label).weight).toBe("bold");
	});

	test("the percentage, the totals and every legend figure are bold in the terminal's own colour", async ($, on) => {
		engine(on);
		await startSession($);

		const { texts } = await drawn($);
		const percent = texts.find((t) => t.text === "30%");
		const totals = texts.find((t) => t.text === "30k/100k");
		const figures = texts.filter((t) => /^\d+k$/u.test(t.text));

		expect(propsOf(percent).color).toBeUndefined();
		expect(propsOf(percent).backgroundColor).toBeUndefined();
		expect(propsOf(percent).weight).toBe("bold");
		expect(propsOf(totals).weight).toBe("bold");
		expect(figures.map((f) => f.text)).toEqual(["6k", "4k", "20k"]);
		expect(figures.every((f) => propsOf(f).weight === "bold")).toBe(true);
	});

	test("the bar is a one-row Image, ten pixels a cell", async ($, on) => {
		engine(on);
		await startSession($);

		const { bar } = await drawn($);
		const source = propsOf(bar).source as { width: number; height: number };

		expect(bar?.type).toBe("Image");
		expect(propsOf(bar).rows).toBe(1);
		expect(source.width).toBe(barWidth(bar) * PX_PER_CELL);
		expect(source.height).toBe(PX_HEIGHT);
	});

	test("each legend key is its category's sample, two cells wide", async ($, on) => {
		engine(on);
		await startSession($);

		const keys = (await drawn($)).images.filter((i) => i.key !== "bar");

		expect(keys.map((k) => propsOf(k).source)).toEqual(
			(["system", "skills", "unattributed"] as const).map((id) =>
				samplePixels(id, SAMPLE_CELLS),
			),
		);
		expect(keys.every((k) => propsOf(k).columns === SAMPLE_CELLS)).toBe(true);
	});
});

describe("counting what the conversation keeps", () => {
	test("a typed prompt shows as user text", async ($, on) => {
		engine(on);
		await startSession($);
		await append($, "prompt", TYPED, 4000);

		expect(await legendText($)).toMatch(/user\s+~1k/u);
	});

	test("a tool result shows as results text, a Read result as read text", async ($, on) => {
		engine(on);
		await startSession($);
		await append($, "tool-result", BASH, 8000);
		await append($, "tool-result", READ, 4000);

		const legend = await legendText($);
		expect(legend).toMatch(/results\s+~2k/u);
		expect(legend).toMatch(/read\s+~1k/u);
	});

	test("a row a subagent's conversation keeps leaves the gauge as it was", async ($, on) => {
		engine(on);
		await startSession($);
		const before = await drawn($);
		await append($, "tool-result", BASH, 8000, "sub");
		const after = await drawn($);

		expect(after.legend).toBe(before.legend);
		expect(after.gauge?.text).toBe(before.gauge?.text);
	});

	test("every row reaches the conversation as it arrived", async ($, on) => {
		const { session } = engine(on);
		await startSession($);
		await append($, "prompt", TYPED, 40);

		expect(session.appended().map((r) => r.message.content)).toEqual([
			[text(40)],
		]);
	});
});

describe("the live total", () => {
	test("a response anchors the totals, and each row appended after it adds to them", async ($, on) => {
		engine(on);
		respond(on, usage(10_000, 20_000, 2000));
		await startSession($);
		await step($);
		await append($, "tool-result", BASH, 4000);

		expect(await gaugeText($)).toMatch(/33k\/100k$/u);
	});

	test("a response's own rows, appended before it resolves, count once", async ($, on) => {
		engine(on);
		respond(on, usage(10_000, 20_000, 2000));
		await startSession($);
		await append($, "response", { kind: "model", model: "test" }, 4000);
		await step($);

		expect(await gaugeText($)).toMatch(/32k\/100k$/u);
	});

	test("a row appended while a request is in flight stays in the total once the response anchors it", async ($, on) => {
		const { clock } = engine(on);
		let arrive: () => void = () => undefined;
		const arrived = new Promise<void>((resolve) => {
			arrive = resolve;
		});
		respond(on, usage(10_000, 20_000, 2000), { arrived });
		await startSession($);
		const inFlight = step($);
		await clock.settle();
		await append($, "delivery", ENGINE, 4000);
		arrive();
		await inFlight;

		expect(await gaugeText($)).toMatch(/33k\/100k$/u);
	});

	test("the output a response's answer leaves unexplained shows as thinking", async ($, on) => {
		engine(on);
		respond(on, usage(27_000, 0, 3000), { answer: "a".repeat(400) });
		await startSession($);
		await step($);

		expect(await legendText($)).toMatch(/thinking\s+~2\.9k/u);
	});

	test("a subagent's response leaves the totals as they were", async ($, on) => {
		engine(on);
		respond(on, usage(10_000, 20_000, 2000));
		await startSession($);
		await step($, "sub");

		expect(await gaugeText($)).toMatch(/30k\/100k$/u);
	});

	test("each response refreshes the breakdown", async ($, on) => {
		engine(on, {
			usage: (call) =>
				usageOf(call === 0 ? ROWS : ROWS.concat(row("MCP tools", 2000))),
		});
		respond(on, usage(10_000, 20_000, 2000));
		await startSession($);
		await step($);

		expect(await legendText($)).toMatch(/mcp\s+/u);
	});

	test("a breakdown that fails to refresh leaves the last one drawn", async ($, on) => {
		engine(on, {
			usage: (call) => {
				if (call > 0) throw new Error("usage unavailable");
				return usageOf(ROWS);
			},
		});
		respond(on, usage(10_000, 20_000, 2000));
		await startSession($);
		await step($);

		const d = await drawn($);
		expect(d.gauge?.text).toMatch(/32k\/100k$/u);
		expect(d.legend).toMatch(/system\s+/u);
	});
});

describe("compaction and /clear", () => {
	test("a compaction shows its compacted total and empties every estimate", async ($, on) => {
		engine(on);
		compactTo(on, 5000);
		await startSession($);
		await append($, "prompt", TYPED, 4000);
		await compact($, "manual");

		const d = await drawn($);
		expect(d.gauge?.text).toMatch(/5k\/100k$/u);
		expect(d.legend).not.toMatch(/user/u);
	});

	test("a compaction's row and SessionStart drop the total a response anchored before it", async ($, on) => {
		engine(on);
		respond(on, usage(10_000, 20_000, 2000));
		await startSession($);
		await step($);
		await append($, "compaction", ENGINE, 8000);
		await $.classic.SessionStart({ source: "compact" });

		expect(await gaugeText($)).toMatch(/30k\/100k$/u);
	});

	test("the compaction's summary row starts the estimates over", async ($, on) => {
		engine(on);
		await startSession($);
		await append($, "prompt", TYPED, 4000);
		await append($, "compaction", ENGINE, 8000);

		const legend = await legendText($);
		expect(legend).toMatch(/summary\s+~2k/u);
		expect(legend).not.toMatch(/user/u);
	});

	for (const order of ["row first", "row last"] as const) {
		test(`the summary outlasts a compaction's other signals, ${order}`, async ($, on) => {
			engine(on);
			compactTo(on, 5000);
			await startSession($);
			await append($, "prompt", TYPED, 4000);
			if (order === "row first") await append($, "compaction", ENGINE, 8000);
			await compact($, "auto");
			await $.classic.SessionStart({ source: "compact" });
			if (order === "row last") await append($, "compaction", ENGINE, 8000);

			const legend = await legendText($);
			expect(legend).toMatch(/summary\s+~2k/u);
			expect(legend).not.toMatch(/user/u);
		});
	}

	for (const kind of ["skipped", "precomputed", "subagent's"] as const) {
		test(`a ${kind} compaction leaves the gauge as it was`, async ($, on) => {
			engine(on);
			compactTo(on, kind === "skipped" ? "skip" : 5000);
			await startSession($);
			await append($, "prompt", TYPED, 4000);
			if (kind === "precomputed") await compact($, "precompute");
			if (kind === "skipped") await compact($, "manual");
			if (kind === "subagent's") await compact($, "auto", "sub");

			const d = await drawn($);
			expect(d.gauge?.text).toMatch(/30k\/100k$/u);
			expect(d.legend).toMatch(/user\s+~1k/u);
		});
	}

	test("/clear empties every estimate, the summary too", async ($, on) => {
		engine(on);
		await startSession($);
		await append($, "compaction", ENGINE, 8000);
		await append($, "prompt", TYPED, 4000);
		expect(await legendText($)).toMatch(/summary.+user/u);
		await $.classic.SessionStart({ source: "clear" });

		const legend = await legendText($);
		expect(legend).not.toMatch(/user/u);
		expect(legend).not.toMatch(/summary/u);
	});
});

describe("the ceiling from settings", () => {
	test("the user source sets the window", async ($, on) => {
		engine(on, {
			window: 1_000_000,
			sources: { user: { autoCompactWindow: 500_000 } },
		});
		await startSession($);

		expect(await gaugeText($)).toMatch(/30k\/500k$/u);
	});

	test("policy, flag, local, project and user sources take precedence in that order", async ($, on) => {
		const sources: Partial<Record<SettingsSource, Settings>> = {
			user: { autoCompactWindow: 800_000 },
			project: { autoCompactWindow: 700_000 },
		};
		engine(on, { window: 1_000_000, sources });
		respond(on, usage(10_000, 19_000, 1000));
		await startSession($);
		expect(await gaugeText($)).toMatch(/30k\/700k$/u);

		const higher: readonly [SettingsSource, string][] = [
			["local", "600k"],
			["flag", "500k"],
			["policy", "400k"],
		];
		for (const [source, figure] of higher) {
			sources[source] = {
				autoCompactWindow: Number.parseInt(figure, 10) * 1000,
			};
			await step($);
			expect(await gaugeText($)).toMatch(new RegExp(`30k/${figure}$`, "u"));
		}
	});

	test("a source that fails to read leaves the engine's threshold", async ($, on) => {
		engine(on, { settingsFail: true });
		await startSession($);

		expect(await gaugeText($)).toMatch(/30k\/100k$/u);
	});

	test("a window past the model's window stops at the model's window", async ($, on) => {
		engine(on, { sources: { user: { autoCompactWindow: 500_000 } } });
		await startSession($);

		expect(await gaugeText($)).toMatch(/30k\/100k$/u);
	});

	test("the model's modelSettings entry beats the top-level window", async ($, on) => {
		engine(on, {
			window: 1_000_000,
			model: "claude-opus-5-5",
			sources: {
				user: {
					autoCompactWindow: 500_000,
					modelSettings: {
						"claude-opus-5-5": { autoCompactWindow: 300_000 },
						"claude-sonnet-5": { autoCompactWindow: 200_000 },
					},
				},
			},
		});
		await startSession($);

		expect(await gaugeText($)).toMatch(/30k\/300k$/u);
	});

	test("CLAUDE_CODE_AUTO_COMPACT_WINDOW beats the settings window", async ($, on) => {
		engine(on, {
			window: 1_000_000,
			variables: [["CLAUDE_CODE_AUTO_COMPACT_WINDOW", "200k"]],
			sources: { user: { autoCompactWindow: 500_000 } },
		});
		await startSession($);

		expect(await gaugeText($)).toMatch(/30k\/200k$/u);
	});

	test("a settings env block beats the shell's variable", async ($, on) => {
		engine(on, {
			window: 1_000_000,
			variables: [["CLAUDE_CODE_AUTO_COMPACT_WINDOW", "200k"]],
			sources: {
				user: {
					env: Object.fromEntries([
						["CLAUDE_CODE_AUTO_COMPACT_WINDOW", "300k"],
					]),
				},
			},
		});
		await startSession($);

		expect(await gaugeText($)).toMatch(/30k\/300k$/u);
	});

	test("DISABLE_AUTO_COMPACT=1 makes the ceiling the model's window", async ($, on) => {
		engine(on, {
			window: 400_000,
			variables: [["DISABLE_AUTO_COMPACT", "1"]],
			sources: { user: { autoCompactWindow: 200_000 } },
		});
		await startSession($);

		expect(await gaugeText($)).toMatch(/30k\/400k$/u);
	});

	test("autoCompactEnabled false makes the ceiling the model's window", async ($, on) => {
		engine(on, {
			window: 400_000,
			sources: {
				user: { autoCompactEnabled: false, autoCompactWindow: 200_000 },
			},
		});
		await startSession($);

		expect(await gaugeText($)).toMatch(/30k\/400k$/u);
	});

	test("CLAUDE_AUTOCOMPACT_PCT_OVERRIDE takes its share of the window", async ($, on) => {
		engine(on, {
			window: 400_000,
			variables: [
				["CLAUDE_CODE_AUTO_COMPACT_WINDOW", "300k"],
				["CLAUDE_AUTOCOMPACT_PCT_OVERRIDE", "50"],
			],
		});
		await startSession($);

		expect(await gaugeText($)).toMatch(/30k\/150k$/u);
	});

	test("a changed source takes effect at the next response", async ($, on) => {
		const sources: Partial<Record<SettingsSource, Settings>> = {
			user: { autoCompactWindow: 500_000 },
		};
		engine(on, { window: 1_000_000, sources });
		respond(on, usage(10_000, 19_000, 1000));
		await startSession($);
		expect(await gaugeText($)).toMatch(/30k\/500k$/u);

		sources.user = { autoCompactWindow: 300_000 };
		await step($);

		expect(await gaugeText($)).toMatch(/30k\/300k$/u);
	});
});

/** Seven categories: the fixture's three, and user, read, results and calls text. */
async function sevenCategories($: Engine): Promise<void> {
	await append($, "prompt", TYPED, 40);
	await append($, "tool-result", READ, 400);
	await append($, "tool-result", BASH, 400);
	await $.session.append({
		door: "response",
		origin: { kind: "model", model: "test" },
		uuid: `row-${rowNumber++}`,
		message: {
			type: "assistant",
			role: "assistant",
			content: [{ type: "tool_use", id: "t", name: "Bash", input: {} }],
		},
	});
}

describe("the layout", () => {
	test("the bar line ends where the legend's widest line ends, on the totals", async ($, on) => {
		engine(on);
		await startSession($);

		const d = await drawn($);
		const widest = widestOf(d.lines.map(lineCells));

		expect(gaugeCells(d)).toBe(widest);
		expect(d.gauge?.text.endsWith("30k/100k")).toBe(true);
	});

	test("each legend item is its key, a space, its label, a space and its figure, LEGEND_GAP cells from the next", async ($, on) => {
		engine(on);
		await startSession($);

		const ui = await mount($);
		const line = await ui.find({ key: "legend-0" });
		const items = await ui.findAll({
			type: "Box",
			text: /^ [a-z]+ ~?[\d.]+[kM]?$/u,
		});
		await ui.unmount();

		expect(items.map((item) => item.text)).toEqual([
			" system 6k",
			" skills 4k",
			" unattributed 20k",
		]);
		expect(propsOf(line).columnGap).toBe(LEGEND_GAP);
	});

	// The fixture's items take 12, 12 and 19 cells: the first two and their
	// gap fit a 30-column row less ROW_INSET, and the third would need 21 more.
	test("the legend breaks onto a new line where the next item would not fit", async ($, on) => {
		engine(on);
		await startSession($);

		const { lines } = await drawn($, { columns: 30, rows: 24 });

		expect(lines.map((l) => l.text)).toEqual([
			" system 6k skills 4k",
			" unattributed 20k",
		]);
	});

	// Two items of 36 and 39 cells and their gap take 77 cells, all an
	// 80-column row leaves, and one cell more breaks the line.
	for (const extra of [0, 1]) {
		test(`at 80 columns, a legend line of ${77 + extra} cells ${extra === 0 ? "fits" : "breaks"}`, async ($, on) => {
			engine(on, {
				rows: [row("a".repeat(30), 1000), row("b".repeat(33 + extra), 1000)],
			});
			await startSession($);

			const { lines } = await drawn($);

			expect(VIEWPORT.columns - ROW_INSET).toBe(77);
			expect(lines).toHaveLength(1 + extra);
		});
	}

	test("with seven categories every legend line fits the row and the bar line spans the widest", async ($, on) => {
		engine(on);
		await startSession($);
		await sevenCategories($);

		const d = await drawn($);
		const widths = d.lines.map(lineCells);
		const items = d.lines.reduce((sum, l) => sum + l.children.length, 0);

		expect(items).toBe(7);
		expect(widestOf(widths)).toBeLessThanOrEqual(VIEWPORT.columns - ROW_INSET);
		expect(gaugeCells(d)).toBe(widestOf(widths));
	});

	test("on a row too narrow for the percentage, the totals and a cell per category, the totals wrap under the bar", async ($, on) => {
		engine(on);
		await startSession($);
		await sevenCategories($);

		const d = await drawn($, { columns: 20, rows: 24 });

		expect(d.totals?.text.trim()).toBe("30k/100k");
		expect(d.gauge?.text).not.toMatch(/100k/u);
		expect(d.gauge?.text.startsWith("30%")).toBe(true);
		expect(barWidth(d.bar)).toBeGreaterThanOrEqual(7);
	});

	test("a bar the legend would stretch past an Image's widest stops at its widest", async ($, on) => {
		engine(on, {
			rows: [row("a".repeat(120), 1000), row("b".repeat(120), 1000)],
		});
		await startSession($);

		const { bar } = await drawn($, { columns: 300, rows: 24 });
		const source = propsOf(bar).source as { width: number };

		expect(barWidth(bar)).toBe(Math.floor(IMAGE_MAX_PX / PX_PER_CELL));
		expect(source.width).toBeLessThanOrEqual(IMAGE_MAX_PX);
	});

	test("a window with nothing used draws no Image", async ($, on) => {
		engine(on, { rows: [] });
		await startSession($);

		const { images, gauge } = await drawn($);

		expect(images).toEqual([]);
		expect(gauge?.text).toMatch(/^0%/u);
	});
});

/** Draws the bar once and lets the blit check it starts settle. */
async function settleBlit($: Engine, clock: MockClock): Promise<void> {
	const ui = await mount($);
	await clock.settle();
	await ui.unmount();
}

const ALT = { deny: "the Image draws its alt here" } as const;

describe("the character fallback", () => {
	test("where the bar Image draws its alt, the bar draws in characters", async ($, on) => {
		const { clock } = engine(on, {
			termProgram: "vscode",
			blit: ALT,
		});
		await startSession($);
		await settleBlit($, clock);

		const { bar, images } = await drawn($);
		const sextants = Object.values(TEXTURE_GLYPHS.sextant).concat(FREE_GLYPH);

		expect(images).toEqual([]);
		expect(bar?.type).toBe("Box");
		expect(Array.from(bar?.text ?? "").every((c) => sextants.includes(c))).toBe(
			true,
		);
	});

	test("each legend key draws its category's characters", async ($, on) => {
		const { clock } = engine(on, {
			termProgram: "Apple_Terminal",
			blit: ALT,
		});
		await startSession($);
		await settleBlit($, clock);

		const ui = await mount($);
		const item = await ui.find({ key: "item-system-system" });
		await ui.unmount();
		const sample = legendSample("system", SAMPLE_CELLS, "bmp");

		expect(item?.children[0]).toEqual({
			type: "Text",
			props: { color: sample.color },
			children: [sample.text],
		});
	});

	test("a tmux that holds images back draws sextants", async ($, on) => {
		const { clock } = engine(on, {
			termProgram: "tmux",
			blit: { deny: "passthrough off", fix: "tmux-passthrough" },
		});
		await startSession($);
		await settleBlit($, clock);

		const { bar } = await drawn($);

		expect(bar?.text.startsWith(TEXTURE_GLYPHS.sextant.solid)).toBe(true);
	});

	test("where the bar Image draws, it stays an Image", async ($, on) => {
		const { clock } = engine(on);
		await startSession($);
		await settleBlit($, clock);

		expect((await drawn($)).bar?.type).toBe("Image");
	});
});
