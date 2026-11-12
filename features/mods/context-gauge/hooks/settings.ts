/** Where auto-compaction runs, resolved from settings files and environment variables as Claude Code resolves them. */

import type { SessionContextBreakdown } from "claude-code";

import type { CompactionSetting } from "../types";

/** A window as a settings file writes it: tokens, or `auto` for the window tuned to the model. */
export type Window = number | "auto";

/** One settings file, reduced to the keys the gauge reads, each kept only where its value is usable. */
export type SettingsLayer = {
	enabled?: boolean;
	window?: Window;
	/** The `autoCompactWindow` of each `modelSettings` entry, by the key it sits under. */
	modelWindows: Readonly<Record<string, Window>>;
	env: Readonly<Record<string, string>>;
};

/** Settings layers combined for one model. */
export type MergedSettings = {
	enabled: boolean;
	window: Window | undefined;
	env: Readonly<Record<string, string>>;
};

/** The shell's value of each variable the gauge reads, named for what it sets. */
export type Shell = Readonly<{
	/** `CLAUDE_CODE_AUTO_COMPACT_WINDOW` */
	window: string | undefined;
	/** `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE` */
	percent: string | undefined;
	/** `DISABLE_AUTO_COMPACT` */
	disableAutoCompact: string | undefined;
	/** `DISABLE_COMPACT` */
	disableCompact: string | undefined;
}>;

/** The smallest and largest auto-compact window, https://code.claude.com/docs/en/model-config#set-the-auto-compact-window */
const MIN_WINDOW = 100_000;
const MAX_WINDOW = 1_000_000;

const TOKEN_COUNT = /^(\d+)([kM])?$/u;

/**
 * The window a `CLAUDE_CODE_AUTO_COMPACT_WINDOW` value sets, or undefined for
 * a value that is no token count.
 *
 * Why: a bare number is tokens, so `200` is 200 tokens and clamps to the
 * minimum; only settings and `/autocompact` read a bare 100 to 1000 as
 * thousands (https://code.claude.com/docs/en/model-config#claude_code_auto_compact_window-values).
 */
export function parseWindow(raw: string | undefined): number | undefined {
	const match = TOKEN_COUNT.exec(raw?.trim() ?? "");
	if (match === null) return undefined;
	const [, digits, suffix] = match;
	const unit = suffix === "k" ? 1000 : suffix === "M" ? 1_000_000 : 1;
	return Math.min(MAX_WINDOW, Math.max(MIN_WINDOW, Number(digits) * unit));
}

const PERCENT = /^\d+(?:\.\d+)?$/u;

/** The percentage a `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE` value sets: 1 to 100, else null. */
function parsePercent(raw: string | undefined): number | null {
	const text = raw?.trim() ?? "";
	if (!PERCENT.test(text)) return null;
	const percent = Number(text);
	return percent >= 1 && percent <= 100 ? percent : null;
}

/** The keys the gauge reads from a settings file, each as the file holds it. */
type RawSettings = {
	autoCompactEnabled?: unknown;
	autoCompactWindow?: unknown;
	modelSettings?: unknown;
	env?: unknown;
};

/** A `modelSettings` entry's key the gauge reads. */
type RawModelEntry = { autoCompactWindow?: unknown };

function isObject(value: unknown): value is object {
	return typeof value === "object" && value !== null && !Array.isArray(value);
}

/** A window a settings file may hold: 100,000 to 1,000,000 tokens, or `auto`. */
function settingsWindow(value: unknown): Window | undefined {
	if (value === "auto") return value;
	if (typeof value === "number" && value >= MIN_WINDOW && value <= MAX_WINDOW) {
		return value;
	}
	return undefined;
}

function parseJson(text: string): unknown {
	try {
		return JSON.parse(text);
	} catch {
		return undefined;
	}
}

/** Reads one settings file's text into its layer; a file that is missing, unparseable or no object gives an empty layer. */
export function parseLayer(text: string | undefined): SettingsLayer {
	const parsed = text === undefined ? undefined : parseJson(text);
	const layer: SettingsLayer = { modelWindows: {}, env: {} };
	if (!isObject(parsed)) return layer;
	const raw: RawSettings = parsed;
	const window = settingsWindow(raw.autoCompactWindow);
	return {
		...(typeof raw.autoCompactEnabled === "boolean"
			? { enabled: raw.autoCompactEnabled }
			: {}),
		...(window === undefined ? {} : { window }),
		modelWindows: Object.fromEntries(
			Object.entries(
				isObject(raw.modelSettings) ? raw.modelSettings : {},
			).flatMap(([model, entry]: [string, unknown]) => {
				const modelEntry: RawModelEntry = isObject(entry) ? entry : {};
				const modelWindow = settingsWindow(modelEntry.autoCompactWindow);
				return modelWindow === undefined ? [] : [[model, modelWindow]];
			}),
		),
		env: Object.fromEntries(
			Object.entries(isObject(raw.env) ? raw.env : {}).flatMap(
				([name, value]: [string, unknown]) =>
					typeof value === "string" ? [[name, value]] : [],
			),
		),
	};
}

/** A model id without its `[1m]` or date suffix, the forms `modelSettings` matches to one entry. */
function canonicalModel(id: string): string {
	return id.replace(/\[1m\]$/iu, "").replace(/-\d{8}$/u, "");
}

/**
 * The window a layer holds for `model`: its `modelSettings` entry, else its
 * top-level key.
 *
 * Hazard: `modelSettings` also matches a model's alias, which the session's
 * model id does not carry, so an alias matches no entry here.
 */
function windowIn(
	layer: SettingsLayer,
	model: string | undefined,
): Window | undefined {
	const entries = Object.entries(layer.modelWindows);
	const entry =
		model === undefined
			? undefined
			: (entries.find(([key]) => key === model) ??
				entries.find(([key]) => canonicalModel(key) === canonicalModel(model)));
	return entry?.[1] ?? layer.window;
}

/**
 * Combines settings layers, highest precedence first, for `model`.
 *
 * Why: a key follows the highest layer that sets it, and a higher scope's
 * window holds against a lower scope's model entry
 * (https://code.claude.com/docs/en/settings#settings-precedence,
 * https://code.claude.com/docs/en/model-config#set-the-auto-compact-window);
 * `env` merges by variable, the higher layer winning
 * (https://code.claude.com/docs/en/env-vars#precedence).
 */
export function mergeSettings(
	layers: readonly SettingsLayer[],
	model: string | undefined,
): MergedSettings {
	return {
		enabled:
			layers.find((layer) => layer.enabled !== undefined)?.enabled ?? true,
		window: layers
			.map((layer) => windowIn(layer, model))
			.find((window) => window !== undefined),
		env: Object.fromEntries(
			layers.toReversed().flatMap((layer) => Object.entries(layer.env)),
		),
	};
}

/**
 * What the merged settings and the shell's variables decide about
 * auto-compaction.
 *
 * Why: a variable in a settings `env` block overwrites the shell's
 * (https://code.claude.com/docs/en/settings-reference#how-env-values-interact-with-your-shell);
 * `DISABLE_AUTO_COMPACT` and `DISABLE_COMPACT` switch it off whatever
 * `autoCompactEnabled` says, and the window variable beats every settings
 * window unless it is no token count
 * (https://code.claude.com/docs/en/env-vars,
 * https://code.claude.com/docs/en/settings-reference#autocompactenabled).
 */
export function resolveCompaction(
	merged: MergedSettings,
	shell: Shell,
): CompactionSetting {
	const variable = (name: string, inShell: string | undefined) =>
		merged.env[name] ?? inShell;
	const settingsWindowSet =
		merged.window === "auto" ? undefined : merged.window;
	return {
		enabled:
			merged.enabled &&
			variable("DISABLE_AUTO_COMPACT", shell.disableAutoCompact) !== "1" &&
			variable("DISABLE_COMPACT", shell.disableCompact) !== "1",
		window:
			parseWindow(variable("CLAUDE_CODE_AUTO_COMPACT_WINDOW", shell.window)) ??
			settingsWindowSet ??
			null,
		percent: parsePercent(
			variable("CLAUDE_AUTOCOMPACT_PCT_OVERRIDE", shell.percent),
		),
	};
}

/**
 * The most tokens the gauge counts toward: where auto-compaction runs, or
 * the whole window where it is off, and never past the window.
 *
 * Why: the percentage takes its share of the window and can only lower the
 * threshold (https://code.claude.com/docs/en/env-vars); the engine's own
 * threshold stands where no window is set, since it holds the model's default.
 */
export function ceiling(
	setting: CompactionSetting,
	b: Pick<SessionContextBreakdown, "rawMaxTokens" | "autoCompactThreshold">,
): number {
	if (!setting.enabled) return b.rawMaxTokens;
	const threshold = setting.window ?? b.autoCompactThreshold ?? b.rawMaxTokens;
	const share =
		setting.percent === null
			? threshold
			: Math.floor(
					((setting.window ?? b.rawMaxTokens) * setting.percent) / 100,
				);
	return Math.min(threshold, share, b.rawMaxTokens);
}
