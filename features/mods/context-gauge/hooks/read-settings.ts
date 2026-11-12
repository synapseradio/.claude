/** Reads the settings sources and environment variables that decide where auto-compaction runs. */

import type { EngineInterface, SettingsSource } from "claude-code";

import type { CompactionSetting } from "../types";
import { mergeSettings, parseLayer, resolveCompaction } from "./settings";

/**
 * The engine's settings sources, highest precedence first: managed policy,
 * the `--settings` flag, local project, project, user.
 *
 * Why: https://code.claude.com/docs/en/settings#settings-precedence
 */
const SOURCES: readonly SettingsSource[] = [
	"policy",
	"flag",
	"local",
	"project",
	"user",
];

/**
 * Where auto-compaction runs for this session: each settings source merged in
 * precedence order, and the environment variables beneath the settings `env`
 * blocks. A source that fails to read contributes nothing.
 */
export async function readCompaction(
	$: EngineInterface,
): Promise<CompactionSetting> {
	const [window, percent, disableAutoCompact, disableCompact, model, ...read] =
		await Promise.all([
			$.env.get("CLAUDE_CODE_AUTO_COMPACT_WINDOW"),
			$.env.get("CLAUDE_AUTOCOMPACT_PCT_OVERRIDE"),
			$.env.get("DISABLE_AUTO_COMPACT"),
			$.env.get("DISABLE_COMPACT"),
			$.session.model().catch(() => undefined),
			...SOURCES.map((source) =>
				$.settings.read({ source }).catch(() => undefined),
			),
		]);
	return resolveCompaction(mergeSettings(read.map(parseLayer), model), {
		window,
		percent,
		disableAutoCompact,
		disableCompact,
	});
}
