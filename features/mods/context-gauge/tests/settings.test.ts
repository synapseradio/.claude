import type { SessionContextBreakdown } from "claude-code";
import { describe, expect, test } from "claude-code/testing";
import type { Shell } from "../hooks/settings";
import {
	ceiling,
	mergeSettings,
	parseLayer,
	parseWindow,
	resolveCompaction,
} from "../hooks/settings";
import type { CompactionSetting } from "../types";

/** A settings layer as the engine reads its source. */
function layer(content: unknown) {
	return parseLayer(content);
}

/** A settings file whose `env` block sets `name` to `value`. */
function envBlock(name: string, value: string) {
	return layer({ env: { [name]: value } });
}

const NO_SHELL: Shell = {
	window: undefined,
	percent: undefined,
	disableAutoCompact: undefined,
	disableCompact: undefined,
};

/** Resolves `layers`, highest precedence first, for `model` against the shell's `variables`. */
function resolve(
	layers: Parameters<typeof mergeSettings>[0],
	variables: Partial<Shell> = {},
	model = "claude-opus-5-5",
): CompactionSetting {
	return resolveCompaction(mergeSettings(layers, model), {
		...NO_SHELL,
		...variables,
	});
}

describe("the window variable", () => {
	test("a plain number is that many tokens", async () => {
		expect(parseWindow("200000")).toBe(200_000);
	});

	test("a plain 200 is 200 tokens, clamped up to 100,000", async () => {
		expect(parseWindow("200")).toBe(100_000);
	});

	test("a k suffix counts thousands", async () => {
		expect(parseWindow("500k")).toBe(500_000);
	});

	test("an M suffix counts millions", async () => {
		expect(parseWindow("1M")).toBe(1_000_000);
	});

	test("a window above 1,000,000 clamps to 1,000,000", async () => {
		expect(parseWindow("2M")).toBe(1_000_000);
	});

	test("a window below 100,000 clamps to 100,000", async () => {
		expect(parseWindow("50k")).toBe(100_000);
	});

	test("a word, an empty string and a negative number are no token count", async () => {
		expect(["auto", "", "lots", "-200000"].map(parseWindow)).toEqual([
			undefined,
			undefined,
			undefined,
			undefined,
		]);
	});

	test("an unset variable is no token count", async () => {
		expect(parseWindow(undefined)).toBeUndefined();
	});
});

describe("a settings source", () => {
	test("an unset source contributes nothing", async () => {
		expect(mergeSettings([parseLayer(undefined)], "m")).toEqual(
			mergeSettings([], "m"),
		);
	});

	test("a value that is no object contributes nothing", async () => {
		const empty = mergeSettings([], "m");
		expect(
			[[1], null, "text", 7].map((value) =>
				mergeSettings([parseLayer(value)], "m"),
			),
		).toEqual([empty, empty, empty, empty]);
	});

	test("a window from 100,000 to 1,000,000 or auto is kept", async () => {
		const windows = [100_000, 1_000_000, "auto"].map(
			(autoCompactWindow) =>
				mergeSettings([layer({ autoCompactWindow })], "m").window,
		);

		expect(windows).toEqual([100_000, 1_000_000, "auto"]);
	});

	test("a window outside the range, or written as text, is dropped", async () => {
		const windows = [99_999, 1_000_001, "500k", "200000", null, true].map(
			(autoCompactWindow) =>
				mergeSettings([layer({ autoCompactWindow })], "m").window,
		);

		expect(windows).toEqual([
			undefined,
			undefined,
			undefined,
			undefined,
			undefined,
			undefined,
		]);
	});

	test("autoCompactEnabled counts only as a boolean", async () => {
		const enabled = [false, "false", 0, null].map(
			(autoCompactEnabled) =>
				mergeSettings([layer({ autoCompactEnabled })], "m").enabled,
		);

		expect(enabled).toEqual([false, true, true, true]);
	});

	test("env keeps its string values and drops the rest", async () => {
		const merged = mergeSettings(
			[layer({ env: { a: "1", b: 2, c: null, d: "" } })],
			"m",
		);

		expect(merged.env).toEqual({ a: "1", d: "" });
	});
});

describe("merged settings", () => {
	test("auto-compaction is on where no file says otherwise", async () => {
		expect(mergeSettings([], "m").enabled).toBe(true);
	});

	test("autoCompactEnabled follows the highest layer that sets it", async () => {
		const managed = layer({ autoCompactEnabled: false });
		const user = layer({ autoCompactEnabled: true });

		expect(mergeSettings([managed, user], "m").enabled).toBe(false);
		expect(mergeSettings([user, managed], "m").enabled).toBe(true);
	});

	test("a layer that leaves autoCompactEnabled out defers to the next", async () => {
		const merged = mergeSettings(
			[layer({}), layer({ autoCompactEnabled: false })],
			"m",
		);

		expect(merged.enabled).toBe(false);
	});

	test("the window follows the highest layer that sets one", async () => {
		const local = layer({ autoCompactWindow: 300_000 });
		const user = layer({ autoCompactWindow: 500_000 });

		expect(mergeSettings([local, user], "m").window).toBe(300_000);
	});

	test("within one layer, the model's window beats the top-level window", async () => {
		const file = layer({
			autoCompactWindow: 500_000,
			modelSettings: { "claude-opus-5-5": { autoCompactWindow: 250_000 } },
		});

		expect(mergeSettings([file], "claude-opus-5-5").window).toBe(250_000);
	});

	test("another model's window leaves the top-level window", async () => {
		const file = layer({
			autoCompactWindow: 500_000,
			modelSettings: { "claude-sonnet-5": { autoCompactWindow: 250_000 } },
		});

		expect(mergeSettings([file], "claude-opus-5-5").window).toBe(500_000);
	});

	test("a higher layer's top-level window beats a lower layer's model window", async () => {
		const managed = layer({ autoCompactWindow: 400_000 });
		const user = layer({
			modelSettings: { "claude-opus-5-5": { autoCompactWindow: 250_000 } },
		});

		expect(mergeSettings([managed, user], "claude-opus-5-5").window).toBe(
			400_000,
		);
	});

	test("auto in a higher layer stops a lower layer's window", async () => {
		const project = layer({ autoCompactWindow: "auto" });
		const user = layer({ autoCompactWindow: 500_000 });

		expect(mergeSettings([project, user], "m").window).toBe("auto");
	});

	test("a model's auto beats the same layer's top-level window", async () => {
		const file = layer({
			autoCompactWindow: 500_000,
			modelSettings: { m: { autoCompactWindow: "auto" } },
		});

		expect(mergeSettings([file], "m").window).toBe("auto");
	});

	test("a key written with [1m] or a date suffix matches the model's id", async () => {
		const keyed = (key: string) =>
			layer({ modelSettings: { [key]: { autoCompactWindow: 250_000 } } });
		const windows = [
			"claude-opus-5-5[1m]",
			"claude-opus-5-5-20261001",
			"claude-opus-5-5",
		].map((key) => mergeSettings([keyed(key)], "claude-opus-5-5").window);

		expect(windows).toEqual([250_000, 250_000, 250_000]);
	});

	test("a session model written with [1m] or a date suffix matches the canonical key", async () => {
		const file = layer({
			modelSettings: { "claude-opus-5-5": { autoCompactWindow: 250_000 } },
		});
		const windows = ["claude-opus-5-5[1m]", "claude-opus-5-5-20261001"].map(
			(model) => mergeSettings([file], model).window,
		);

		expect(windows).toEqual([250_000, 250_000]);
	});

	test("an alias the session model carries matches no entry, leaving the top-level window", async () => {
		const file = layer({
			autoCompactWindow: 500_000,
			modelSettings: { "claude-opus-5-5": { autoCompactWindow: 250_000 } },
		});

		expect(mergeSettings([file], "opus").window).toBe(500_000);
	});

	test("env merges by variable, the higher layer winning each", async () => {
		const local = layer({ env: { a: "local" } });
		const user = layer({ env: { a: "user", b: "user" } });

		expect(mergeSettings([local, user], "m").env).toEqual({
			a: "local",
			b: "user",
		});
	});
});

describe("the compaction a session resolves", () => {
	test("by default auto-compaction is on with no window and no percentage", async () => {
		expect(resolve([])).toEqual({ enabled: true, window: null, percent: null });
	});

	test("autoCompactEnabled false turns it off", async () => {
		expect(resolve([layer({ autoCompactEnabled: false })]).enabled).toBe(false);
	});

	test("DISABLE_AUTO_COMPACT=1 turns it off, over autoCompactEnabled true", async () => {
		const file = layer({ autoCompactEnabled: true });

		expect(resolve([file], { disableAutoCompact: "1" }).enabled).toBe(false);
	});

	test("DISABLE_COMPACT=1 turns it off", async () => {
		expect(resolve([], { disableCompact: "1" }).enabled).toBe(false);
	});

	test("a disable variable set to anything but 1 leaves it on", async () => {
		expect(
			resolve([], { disableAutoCompact: "0", disableCompact: "" }).enabled,
		).toBe(true);
	});

	test("a variable in a settings env block beats the shell's", async () => {
		const file = envBlock("DISABLE_AUTO_COMPACT", "0");

		expect(resolve([file], { disableAutoCompact: "1" }).enabled).toBe(true);
	});

	test("a variable in a settings env block applies where the shell sets none", async () => {
		const file = envBlock("DISABLE_COMPACT", "1");

		expect(resolve([file]).enabled).toBe(false);
	});

	test("the shell's variable applies where no settings env block sets it", async () => {
		const file = envBlock("OTHER", "1");

		expect(resolve([file], { disableCompact: "1" }).enabled).toBe(false);
	});

	test("the window variable beats every settings window", async () => {
		const file = layer({
			autoCompactWindow: 500_000,
			modelSettings: { "claude-opus-5-5": { autoCompactWindow: 250_000 } },
		});

		expect(resolve([file], { window: "300k" }).window).toBe(300_000);
	});

	test("a window variable of 200 reads as 200 tokens, clamped, where the settings window says 500,000", async () => {
		const file = layer({ autoCompactWindow: 500_000 });

		expect(resolve([file], { window: "200" }).window).toBe(100_000);
	});

	test("a window variable that is no token count leaves the settings window", async () => {
		const file = layer({ autoCompactWindow: 500_000 });

		expect(resolve([file], { window: "auto" }).window).toBe(500_000);
	});

	test("the settings window applies where the variable is unset", async () => {
		expect(resolve([layer({ autoCompactWindow: 500_000 })]).window).toBe(
			500_000,
		);
	});

	test("a settings window of auto leaves no window", async () => {
		expect(resolve([layer({ autoCompactWindow: "auto" })]).window).toBeNull();
	});

	test("the percentage variable takes a number from 1 to 100", async () => {
		const percents = ["1", "50", "100"].map(
			(pct) => resolve([], { percent: pct }).percent,
		);

		expect(percents).toEqual([1, 50, 100]);
	});

	test("a percentage outside 1 to 100, or no number, applies to nothing", async () => {
		const percents = ["0", "101", "-5", "half", ""].map(
			(pct) => resolve([], { percent: pct }).percent,
		);

		expect(percents).toEqual([null, null, null, null, null]);
	});
});

/** A breakdown of a window of `rawMaxTokens`, whose engine threshold is `autoCompactThreshold` where given. */
function windowOf(
	rawMaxTokens: number,
	autoCompactThreshold?: number,
): Pick<SessionContextBreakdown, "rawMaxTokens" | "autoCompactThreshold"> {
	return autoCompactThreshold === undefined
		? { rawMaxTokens }
		: { rawMaxTokens, autoCompactThreshold };
}

const ON: CompactionSetting = { enabled: true, window: null, percent: null };

describe("the ceiling", () => {
	test("with nothing set, the ceiling is the engine's threshold", async () => {
		expect(ceiling(ON, windowOf(1_000_000, 967_000))).toBe(967_000);
	});

	test("with nothing set and no engine threshold, the ceiling is the raw window", async () => {
		expect(ceiling(ON, windowOf(200_000))).toBe(200_000);
	});

	test("a settings window replaces the engine's threshold", async () => {
		const setting = { ...ON, window: 500_000 };

		expect(ceiling(setting, windowOf(1_000_000, 967_000))).toBe(500_000);
	});

	test("with auto-compaction off, the ceiling is the raw window, whatever the window says", async () => {
		const setting = { enabled: false, window: 300_000, percent: 50 };

		expect(ceiling(setting, windowOf(1_000_000, 967_000))).toBe(1_000_000);
	});

	test("the raw window caps a settings window", async () => {
		const setting = { ...ON, window: 500_000 };

		expect(ceiling(setting, windowOf(200_000))).toBe(200_000);
	});

	test("the percentage takes its share of the settings window", async () => {
		const setting = { ...ON, window: 500_000, percent: 50 };

		expect(ceiling(setting, windowOf(1_000_000))).toBe(250_000);
	});

	test("the percentage rounds down to a whole token", async () => {
		const setting = { ...ON, window: 100_001, percent: 50 };

		expect(ceiling(setting, windowOf(1_000_000))).toBe(50_000);
	});

	test("with no window set, the percentage takes its share of the raw window", async () => {
		const setting = { ...ON, percent: 50 };

		expect(ceiling(setting, windowOf(1_000_000, 967_000))).toBe(500_000);
	});

	test("the percentage cannot raise the ceiling past the engine's threshold", async () => {
		const setting = { ...ON, percent: 100 };

		expect(ceiling(setting, windowOf(1_000_000, 967_000))).toBe(967_000);
	});

	test("the percentage cannot raise a settings window", async () => {
		const setting = { ...ON, window: 300_000, percent: 100 };

		expect(ceiling(setting, windowOf(1_000_000))).toBe(300_000);
	});
});
