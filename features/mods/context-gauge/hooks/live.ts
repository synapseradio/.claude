/** The gauge's usage model: the engine's fixed rows beside the window's message categories, against the ceiling auto-compaction runs at. */

import type { SessionContextBreakdown, SessionContextUsage } from "claude-code";

import type {
	CompactionSetting,
	Ratio,
	UsageCategory,
	UsageModel,
	Window,
} from "../types";
import { ceiling } from "./settings";
import { drawn } from "./window";

/** The breakdown row the gauge's own message categories stand in for. */
const MESSAGES_ROW = "Messages";

/** The breakdown's `used` rows other than Messages: the system prompt, tools, MCP, memory, skills and any the gauge does not name. */
export function fixedRows(breakdown: SessionContextBreakdown): UsageCategory[] {
	return breakdown.categories
		.filter((c) => c.kind === "used" && c.name !== MESSAGES_ROW)
		.map((c) => ({ name: c.name, tokens: c.tokens }));
}

function tokensOf(rows: readonly UsageCategory[]): number {
	return rows.reduce((sum, c) => sum + c.tokens, 0);
}

/** The tokens of the breakdown's fixed rows together. */
export function fixedTokens(breakdown: SessionContextBreakdown): number {
	return tokensOf(fixedRows(breakdown));
}

/** The gauge's usage model, or null without a breakdown or a ceiling; the ceiling is where `compaction` says auto-compaction runs (see `ceiling`). */
export function usageModel(
	context: SessionContextUsage,
	window: Window,
	ratio: Ratio,
	compaction: CompactionSetting,
): UsageModel | null {
	const breakdown = context.breakdown;
	if (breakdown === undefined) return null;
	const max = ceiling(compaction, breakdown);
	if (max <= 0) return null;
	const fixed = fixedRows(breakdown);
	const figures = drawn(window, ratio, tokensOf(fixed));
	const used = Math.round(figures.used);
	const percent = Math.max(0, Math.min(100, Math.round((used / max) * 100)));
	return {
		used,
		max,
		percent,
		measured: figures.measured,
		fixed,
		messages: figures.messages,
		gap: figures.gap,
	};
}
