import type { ContextCategory, On } from "claude-code";
import type { Engine } from "claude-code/testing";
import { describe, expect, test } from "claude-code/testing";

import { CATEGORY_STYLES } from "../hooks/palette";

/** A bar cell: the sextant filling a cell's middle third, U+1FB0B. */
const BAR_CELL = /\u{1FB0B}/u;

/** Cells a drawn string takes: one per code point, the bar's astral glyph included. */
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

const ICONS = /[○◔◑◕●⊞⚙⇄◇▤✦✉]/u;

function row(
	name: string,
	tokens: number,
	kind: ContextCategory["kind"] = "used",
): ContextCategory {
	return { name, tokens, color: "inactive", isDeferred: false, kind };
}

// Stands for the engine beneath the plugin: a session whose window holds
// 30,000 of 100,000 tokens, 20,000 of them messages.
function engine(on: On): void {
	on("session.start", (_, e) => ({ cwd: e.cwd }));
	on("env.get", () => ({ value: undefined }));
	on("classic.SessionStart", () => ({}));
	on("prompt.submit", (_, e) => ({ text: e.text }));
	on("session.usage", () => ({
		value: {
			startedAt: 0,
			rateLimits: [],
			context: {
				tokens: 30_000,
				window: 100_000,
				breakdown: {
					categories: [
						row("System prompt", 6000),
						row("Skills", 4000),
						row("Messages", 20_000),
						row("Free space", 70_000, "free"),
					],
					totalTokens: 30_000,
					maxTokens: 100_000,
					rawMaxTokens: 100_000,
					autocompactSource: "model-default",
					percentage: 30,
					gridRows: [],
					model: "test",
					memoryFiles: [],
					mcpTools: [],
					agents: [],
					isAutoCompactEnabled: false,
					apiUsage: null,
				},
			},
		},
	}));
	on("ui.render", ($, e) => {
		const { Text } = $.ui.resolve(e);
		return <Text>engine hint line</Text>;
	});
}

const TYPED = { wait: false, origin: { kind: "composer" } } as const;

/** Starts an interactive terminal session, the one every test draws in. */
async function startSession($: Engine): Promise<void> {
	await $.session.start({ cwd: "/", surface: "terminal", isInteractive: true });
}

/** Answers every tool call with a result the model reads as `chars` characters. */
function answerToolCalls(on: On, chars: number): void {
	on("tool.call", () => ({ result: {}, text: "r".repeat(chars) }));
}

type DrawnProps = {
	color?: unknown;
	backgroundColor?: unknown;
	weight?: unknown;
	columnGap?: unknown;
};

/** The props the gauge's tests read off a drawn element, none where the node is absent. */
function propsOf(node: { props: DrawnProps } | undefined): DrawnProps {
	return node?.props ?? {};
}

const VIEWPORT = { columns: 80, rows: 24 } as const;

/** The bar line's text and the legend's text, drawn 80 cells wide. */
async function drawn($: Engine): Promise<{ gauge: string; legend: string }> {
	const ui = await $.ui.mount({ ...HINT, viewport: VIEWPORT });
	const gauge = (await ui.find({ key: "gauge" }))?.text ?? "";
	const legend = (await ui.find({ key: "legend" }))?.text ?? "";
	await ui.unmount();
	return { gauge, legend };
}

async function legendText($: Engine): Promise<string> {
	return (await drawn($)).legend;
}

describe("the gauge under the prompt", () => {
	test("sits on its own line beneath the engine hint line, percentage first, no icons", async ($, on) => {
		engine(on);
		await startSession($);

		const ui = await $.ui.mount(HINT);
		const texts = (await ui.findAll({ type: "Text" })).map((t) => t.text);
		const gauge = (await ui.find({ key: "gauge" }))?.text ?? "";
		await ui.unmount();

		expect(texts[0]).toBe("engine hint line");
		expect(gauge.trimStart().startsWith("30%")).toBe(true);
		expect(ICONS.test(texts.join(""))).toBe(false);
	});

	test("each category label is bold in its bar segment colour, with no background", async ($, on) => {
		engine(on);
		await startSession($);

		const ui = await $.ui.mount(HINT);
		const label = await ui.find({ type: "Text", text: "system" });
		const segments = await ui.findAll({ type: "Text", text: BAR_CELL });
		await ui.unmount();

		expect(propsOf(label).color).toBe(CATEGORY_STYLES.system.swatch.hex);
		expect(propsOf(label).backgroundColor).toBeUndefined();
		expect(propsOf(label).weight).toBe("bold");
		expect(propsOf(segments[0]).color).toBe(CATEGORY_STYLES.system.swatch.hex);
	});

	test("the percentage, the totals and every legend figure are bold in the terminal's own colour", async ($, on) => {
		engine(on);
		await startSession($);

		const ui = await $.ui.mount(HINT);
		const percent = await ui.find({ type: "Text", text: "30%" });
		const totals = await ui.find({ type: "Text", text: "30k/100k" });
		const figures = await ui.findAll({ type: "Text", text: /^\d+k$/u });
		await ui.unmount();

		expect(propsOf(percent).color).toBeUndefined();
		expect(propsOf(percent).backgroundColor).toBeUndefined();
		expect(propsOf(percent).weight).toBe("bold");
		expect(propsOf(totals).weight).toBe("bold");
		expect(figures.map((f) => f.text)).toEqual(["6k", "4k", "20k"]);
		expect(figures.every((f) => propsOf(f).weight === "bold")).toBe(true);
	});

	test("the bar is one vertically centred cell high, free space in the same glyph", async ($, on) => {
		engine(on);
		await startSession($);

		const ui = await $.ui.mount({ ...HINT, viewport: VIEWPORT });
		const bar = (await ui.find({ key: "bar" }))?.text ?? "";
		await ui.unmount();

		expect(bar).toMatch(/^\u{1FB0B}+$/u);
	});

	test("a submitted prompt shows as user text", async ($, on) => {
		engine(on);
		await startSession($);
		await $.prompt.submit({ ...TYPED, text: "x".repeat(4000) });

		expect(await legendText($)).toMatch(/user\s+~1k/u);
	});

	test("a tool call shows its input as calls text and its result as results text", async ($, on) => {
		engine(on);
		answerToolCalls(on, 8000);
		await startSession($);
		await $.tool.call({
			tool: "Bash",
			command: "x".repeat(400 - 'Bash{"command":""}'.length),
		});

		const legend = await legendText($);
		expect(legend).toMatch(/calls\s+~100/u);
		expect(legend).toMatch(/results\s+~2k/u);
	});

	test("a Read result shows as read text, apart from other results", async ($, on) => {
		engine(on);
		answerToolCalls(on, 8000);
		await startSession($);
		await $.tool.call({ tool: "Read", file_path: "/a" });

		const legend = await legendText($);
		expect(legend).toMatch(/read\s+~2k/u);
		expect(legend).not.toMatch(/results/u);
	});

	test("a call a subagent makes leaves the gauge as it was", async ($, on) => {
		engine(on);
		answerToolCalls(on, 8000);
		await startSession($);
		const before = await legendText($);
		await $.tool.call({
			tool: "Bash",
			command: "x".repeat(400),
			agentId: "sub",
		});

		expect(await legendText($)).toBe(before);
	});

	test("hook context shows as hooks text, unless it reached a subagent", async ($, on) => {
		engine(on);
		on("classic.UserPromptSubmit", () => ({
			additionalContext: ["y".repeat(12_000)],
		}));
		await startSession($);
		await $.classic.UserPromptSubmit({ prompt: "hi" });
		await $.classic.UserPromptSubmit({ prompt: "hi", agent_id: "sub" });

		expect(await legendText($)).toMatch(/hooks\s+~3k/u);
	});

	test("compaction clears the estimates", async ($, on) => {
		engine(on);
		await startSession($);
		await $.prompt.submit({ ...TYPED, text: "x".repeat(4000) });
		await $.classic.SessionStart({ source: "compact" });

		expect(await legendText($)).not.toMatch(/user/u);
	});

	// The fixture's legend reads `system 6k`, `skills 4k`, `replies 20k` with
	// 2-cell gaps between items: 9 + 2 + 9 + 2 + 11 = 33 cells.
	test("the bar line ends where the legend's last item ends, on the abbreviated totals", async ($, on) => {
		engine(on);
		await startSession($);

		const { gauge, legend } = await drawn($);

		expect(cells(gauge)).toBe(33);
		expect(gauge.endsWith("30k/100k")).toBe(true);
		expect(`${gauge}${legend}`).not.toMatch(/comfy/u);
	});

	test("each legend item is its label, one space and its figure, two cells from the next", async ($, on) => {
		engine(on);
		await startSession($);

		const ui = await $.ui.mount({ ...HINT, viewport: VIEWPORT });
		const line = await ui.find({ key: "legend-0" });
		const items = await ui.findAll({
			type: "Box",
			text: /^[a-z]+ ~?[\d.]+[kM]?$/u,
		});
		await ui.unmount();

		expect(items.map((item) => item.text)).toEqual([
			"system 6k",
			"skills 4k",
			"replies 20k",
		]);
		expect(propsOf(line).columnGap).toBe(2);
	});

	// 30 columns leave 27 cells: `system 6k` and `skills 4k` take 20, and
	// `replies 20k` would need 13 more.
	test("the legend breaks onto a new line where the next item would not fit", async ($, on) => {
		engine(on);
		await startSession($);

		const ui = await $.ui.mount({
			...HINT,
			viewport: { columns: 30, rows: 24 },
		});
		const first = await ui.find({ key: "legend-0" });
		const second = await ui.find({ key: "legend-1" });
		await ui.unmount();

		expect(first?.text).toBe("system 6kskills 4k");
		expect(second?.text).toBe("replies 20k");
	});

	test("the bar clips at the row's edge where the row is narrower than measured", async ($, on) => {
		engine(on);
		await startSession($);

		const ui = await $.ui.mount({ ...HINT, viewport: VIEWPORT });
		const bar = await ui.find({ key: "bar" });
		await ui.unmount();

		expect(bar?.props).toMatchObject({
			overflow: "hidden",
			height: 1,
			flexShrink: 1,
		});
	});

	test("every category in the legend owns a bar segment in its colour", async ($, on) => {
		engine(on);
		answerToolCalls(on, 400);
		await startSession($);
		await $.prompt.submit({ ...TYPED, text: "x".repeat(40) });
		await $.tool.call({ tool: "Read", file_path: "/a" });
		await $.tool.call({ tool: "Bash", command: "ls" });

		const ui = await $.ui.mount({ ...HINT, viewport: VIEWPORT });
		const segments = await ui.findAll({ type: "Text", text: BAR_CELL });
		const labels = await ui.findAll({ type: "Text", text: /^[a-z]+$/u });
		await ui.unmount();

		const segmentColors = new Set(segments.map((s) => propsOf(s).color));
		expect(labels).toHaveLength(7);
		for (const label of labels) {
			expect(segmentColors.has(propsOf(label).color)).toBe(true);
		}
	});

	test("with seven categories every legend line fits the row and the bar line matches the widest", async ($, on) => {
		engine(on);
		answerToolCalls(on, 400);
		await startSession($);
		await $.prompt.submit({ ...TYPED, text: "x".repeat(40) });
		await $.tool.call({ tool: "Read", file_path: "/a" });
		await $.tool.call({ tool: "Bash", command: "ls" });

		const ui = await $.ui.mount({ ...HINT, viewport: VIEWPORT });
		const gauge = (await ui.find({ key: "gauge" }))?.text ?? "";
		const lines: { text: string; children: unknown[] }[] = [];
		for (let n = 0; ; n++) {
			const line = await ui.find({ key: `legend-${n}` });
			if (line === undefined) break;
			lines.push(line);
		}
		await ui.unmount();

		// A line draws its items' text plus a 2-cell gap between each pair.
		const widths = lines.map(
			(line) => cells(line.text) + 2 * (line.children.length - 1),
		);
		const items = lines.reduce((sum, line) => sum + line.children.length, 0);
		expect(items).toBe(7);
		const widest = widths.reduce((most, w) => Math.max(most, w), 0);
		expect(widest).toBeLessThanOrEqual(VIEWPORT.columns - 3);
		expect(cells(gauge)).toBe(widest);
	});
});
