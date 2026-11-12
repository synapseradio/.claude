import type { ContextCategory, On } from "claude-code";
import type { Engine } from "claude-code/testing";
import { describe, expect, test } from "claude-code/testing";

import { CATEGORY_SWATCHES, CHIP_TEXT, FILL_SWATCHES } from "../hooks/palette";

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

type TextColors = { color?: unknown; backgroundColor?: unknown };

/** The colour props of a drawn Text, none where the node is absent. */
function colors(node: { props: TextColors } | undefined): TextColors {
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
		await $.session.start({
			cwd: "/",
			surface: "terminal",
			isInteractive: true,
		});

		const ui = await $.ui.mount(HINT);
		const texts = (await ui.findAll({ type: "Text" })).map((t) => t.text);
		const gauge = (await ui.find({ key: "gauge" }))?.text ?? "";
		await ui.unmount();

		expect(texts[0]).toBe("engine hint line");
		expect(gauge.trimStart().startsWith("30%")).toBe(true);
		expect(ICONS.test(texts.join(""))).toBe(false);
	});

	test("each category word is a chip in its bar segment colour, black text on it", async ($, on) => {
		engine(on);
		await $.session.start({
			cwd: "/",
			surface: "terminal",
			isInteractive: true,
		});

		const ui = await $.ui.mount(HINT);
		const chip = await ui.find({ type: "Text", text: "system" });
		const percent = await ui.find({ type: "Text", text: "30%" });
		const segments = await ui.findAll({ type: "Text", text: /▓/u });
		await ui.unmount();

		expect(colors(chip).backgroundColor).toBe(CATEGORY_SWATCHES.system.hex);
		expect(colors(chip).color).toBe(CHIP_TEXT);
		expect(colors(segments[0]).color).toBe(CATEGORY_SWATCHES.system.hex);
		expect(colors(percent).color).toBe(FILL_SWATCHES.low.hex);
		expect(colors(percent).backgroundColor).toBeUndefined();
	});

	test("a submitted prompt shows as user text", async ($, on) => {
		engine(on);
		await $.session.start({
			cwd: "/",
			surface: "terminal",
			isInteractive: true,
		});
		await $.prompt.submit({ ...TYPED, text: "x".repeat(4000) });

		expect(await legendText($)).toMatch(/user\s+~1k/u);
	});

	test("a tool call shows its input as calls text and its result as results text", async ($, on) => {
		engine(on);
		on("tool.call", () => ({ result: {}, text: "r".repeat(8000) }));
		await $.session.start({
			cwd: "/",
			surface: "terminal",
			isInteractive: true,
		});
		await $.tool.call({
			tool: "Bash",
			command: "x".repeat(400 - 'Bash{"command":""}'.length),
		});

		const gauge = await legendText($);
		expect(gauge).toMatch(/calls\s+~100/u);
		expect(gauge).toMatch(/results\s+~2k/u);
	});

	test("a Read result shows as read text, apart from other results", async ($, on) => {
		engine(on);
		on("tool.call", () => ({ result: {}, text: "r".repeat(8000) }));
		await $.session.start({
			cwd: "/",
			surface: "terminal",
			isInteractive: true,
		});
		await $.tool.call({ tool: "Read", file_path: "/a" });

		const gauge = await legendText($);
		expect(gauge).toMatch(/read\s+~2k/u);
		expect(gauge).not.toMatch(/results/u);
	});

	test("a call a subagent makes leaves the gauge as it was", async ($, on) => {
		engine(on);
		on("tool.call", () => ({ result: {}, text: "r".repeat(8000) }));
		await $.session.start({
			cwd: "/",
			surface: "terminal",
			isInteractive: true,
		});
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
		await $.session.start({
			cwd: "/",
			surface: "terminal",
			isInteractive: true,
		});
		await $.classic.UserPromptSubmit({ prompt: "hi" });
		await $.classic.UserPromptSubmit({ prompt: "hi", agent_id: "sub" });

		expect(await legendText($)).toMatch(/hooks\s+~3k/u);
	});

	test("compaction clears the estimates", async ($, on) => {
		engine(on);
		await $.session.start({
			cwd: "/",
			surface: "terminal",
			isInteractive: true,
		});
		await $.prompt.submit({ ...TYPED, text: "x".repeat(4000) });
		await $.classic.SessionStart({ source: "compact" });

		expect(await legendText($)).not.toMatch(/user/u);
	});

	// A legend item is 15 cells and the gap between items 3, so N grid columns
	// span N * 15 + (N - 1) * 3 cells. The hint row draws 3 cells narrower than
	// the terminal. At 80 columns, 77 cells hold 4 grid columns; at 200, 197
	// cells hold 11. The bar line spans one grid column fewer than fits.
	test("the bar line spans one grid column fewer than fit and ends on the abbreviated totals", async ($, on) => {
		engine(on);
		await $.session.start({
			cwd: "/",
			surface: "terminal",
			isInteractive: true,
		});

		const { gauge, legend } = await drawn($);

		expect(gauge).toHaveLength(3 * 15 + 2 * 3);
		expect(gauge.endsWith("30k/100k")).toBe(true);
		expect(`${gauge}${legend}`).not.toMatch(/comfy/u);
	});

	test("on a wide terminal the bar line still ends one grid column short", async ($, on) => {
		engine(on);
		await $.session.start({
			cwd: "/",
			surface: "terminal",
			isInteractive: true,
		});

		const ui = await $.ui.mount({
			...HINT,
			viewport: { columns: 200, rows: 50 },
		});
		const gauge = (await ui.find({ key: "gauge" }))?.text ?? "";
		await ui.unmount();

		expect(gauge).toHaveLength(10 * 15 + 9 * 3);
	});

	test("the bar clips at the row's edge where the row is narrower than measured", async ($, on) => {
		engine(on);
		await $.session.start({
			cwd: "/",
			surface: "terminal",
			isInteractive: true,
		});

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
		on("tool.call", () => ({ result: {}, text: "r".repeat(400) }));
		await $.session.start({
			cwd: "/",
			surface: "terminal",
			isInteractive: true,
		});
		await $.prompt.submit({ ...TYPED, text: "x".repeat(40) });
		await $.tool.call({ tool: "Read", file_path: "/a" });
		await $.tool.call({ tool: "Bash", command: "ls" });

		const ui = await $.ui.mount({ ...HINT, viewport: VIEWPORT });
		const legend = await ui.find({ key: "legend" });
		const segments = await ui.findAll({ type: "Text", text: /▓/u });
		const chips = (
			await ui.findAll({ type: "Text", text: /^ [a-z]+ +$/u })
		).filter((chip) => legend?.text.includes(chip.text) === true);
		await ui.unmount();

		const segmentColors = new Set(segments.map((s) => colors(s).color));
		expect(chips).toHaveLength(7);
		for (const chip of chips) {
			expect(segmentColors.has(colors(chip).backgroundColor)).toBe(true);
		}
	});

	test("the legend lays seven categories out as aligned lines of four and three at 80 columns", async ($, on) => {
		engine(on);
		on("tool.call", () => ({ result: {}, text: "r".repeat(400) }));
		await $.session.start({
			cwd: "/",
			surface: "terminal",
			isInteractive: true,
		});
		await $.prompt.submit({ ...TYPED, text: "x".repeat(40) });
		await $.tool.call({ tool: "Read", file_path: "/a" });
		await $.tool.call({ tool: "Bash", command: "ls" });

		const ui = await $.ui.mount({ ...HINT, viewport: VIEWPORT });
		const first = await ui.find({ key: "legend-0" });
		const second = await ui.find({ key: "legend-1" });
		const third = await ui.find({ key: "legend-2" });
		await ui.unmount();

		expect(first?.children).toHaveLength(4);
		expect(second?.children).toHaveLength(3);
		expect(third).toBeUndefined();
	});
});
