/** The gauge's live figures: the window a response left, the thinking it spent, and the usage model drawn from them. */

import type {
	ModelUsage,
	SessionContextBreakdown,
	SessionContextUsage,
	TurnStepResult,
} from "claude-code";

import type { UsageModel } from "../types";

const CHARS_PER_TOKEN = 4;

/** The window as one response left it: input + cache read + cache creation + output tokens. */
export function windowAfter(usage: ModelUsage): number {
	return (
		usage.input_tokens +
		usage.cache_read_input_tokens +
		usage.cache_creation_input_tokens +
		usage.output_tokens
	);
}

/**
 * Thinking tokens one response spent: output tokens less the visible answer
 * and the tool calls, at four characters a token, never below 0.
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
 * Why: the breakdown's `autoCompactThreshold` ignores
 * CLAUDE_AUTOCOMPACT_PCT_OVERRIDE, so the ceiling comes from the override, a
 * percentage of the window
 * (https://code.claude.com/docs/en/env-vars).
 */
function effectiveMax(
	b: SessionContextBreakdown,
	pctRaw: string | undefined,
): number {
	const pct = pctRaw ? Number(pctRaw) : Number.NaN;
	if (Number.isFinite(pct) && pct > 0 && pct <= 100) {
		return Math.floor((b.rawMaxTokens * pct) / 100);
	}
	return b.autoCompactThreshold ?? b.rawMaxTokens;
}

/** The gauge's model: used = anchor + pending / 4 once a response anchored it, else the breakdown's total; categories scaled to used; max from CLAUDE_AUTOCOMPACT_PCT_OVERRIDE or the breakdown. */
export function usageModel(
	context: SessionContextUsage,
	live: { anchor: number | null; pending: number },
	pctRaw: string | undefined,
): UsageModel | null {
	const b = context.breakdown;
	if (b === undefined) return null;
	const max = effectiveMax(b, pctRaw);
	if (max <= 0) return null;
	const used =
		live.anchor === null
			? b.totalTokens
			: Math.round(live.anchor + live.pending / CHARS_PER_TOKEN);
	const percent = Math.max(0, Math.min(100, Math.round((used / max) * 100)));
	const scale = b.totalTokens > 0 ? used / b.totalTokens : 1;
	const categories = b.categories
		.filter((c) => c.kind === "used" && c.tokens > 0)
		.map((c) => ({ name: c.name, tokens: Math.round(c.tokens * scale) }));
	return { used, max, percent, categories };
}
