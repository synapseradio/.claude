/** The gauge's live figures: the window a response left, the thinking it spent, and the usage model drawn from them. */

import type {
	ModelUsage,
	SessionContextBreakdown,
	SessionContextUsage,
	TurnStepResult,
} from "claude-code";

import type { UsageModel } from "../types";

const CHARS_PER_TOKEN = 4;

/** The window as one response left it, its own output included. */
export function windowAfter(usage: ModelUsage): number {
	return (
		usage.input_tokens +
		usage.cache_read_input_tokens +
		usage.cache_creation_input_tokens +
		usage.output_tokens
	);
}

/**
 * Thinking tokens one response spent: the output tokens its visible answer
 * and tool calls leave unexplained.
 *
 * Why: the API bills the full thinking while the transcript keeps at most a
 * summary of it, so only `output_tokens` measures it
 * (https://platform.claude.com/docs/en/build-with-claude/thinking#summarized-thinking).
 */
export function thinkingTokens(
	step: Pick<TurnStepResult, "answer" | "toolUses" | "usage">,
): number {
	if (step.usage === null) return 0;
	const visible = step.toolUses.reduce(
		(chars, toolUse) => chars + JSON.stringify(toolUse).length,
		step.answer.length,
	);
	return Math.max(
		0,
		Math.round(step.usage.output_tokens - visible / CHARS_PER_TOKEN),
	);
}

/**
 * Why: CLAUDE_AUTOCOMPACT_PCT_OVERRIDE sets the percentage of the window at
 * which compaction runs, and can lower the threshold but never raise it
 * (https://code.claude.com/docs/en/env-vars).
 *
 * Hazard: the breakdown's `autoCompactThreshold` leaves the override out.
 */
function effectiveMax(
	b: SessionContextBreakdown,
	pctRaw: string | undefined,
): number {
	const threshold = b.autoCompactThreshold ?? b.rawMaxTokens;
	const pct = pctRaw ? Number(pctRaw) : Number.NaN;
	if (Number.isFinite(pct) && pct > 0 && pct <= 100) {
		return Math.min(threshold, Math.floor((b.rawMaxTokens * pct) / 100));
	}
	return threshold;
}

/** The gauge's usage model, live from the last anchoring response, or null without a breakdown or a ceiling. */
export function usageModel(
	context: SessionContextUsage,
	live: { anchor: number | null; pending: number },
	pctRaw: string | undefined,
): UsageModel | null {
	const breakdown = context.breakdown;
	if (breakdown === undefined) return null;
	const max = effectiveMax(breakdown, pctRaw);
	if (max <= 0) return null;
	const used =
		live.anchor === null
			? breakdown.totalTokens
			: Math.round(live.anchor + live.pending / CHARS_PER_TOKEN);
	const percent = Math.max(0, Math.min(100, Math.round((used / max) * 100)));
	const scale = breakdown.totalTokens > 0 ? used / breakdown.totalTokens : 1;
	const categories = breakdown.categories
		.filter((c) => c.kind === "used" && c.tokens > 0)
		.map((c) => ({ name: c.name, tokens: Math.round(c.tokens * scale) }));
	return { used, max, percent, categories };
}
