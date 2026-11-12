/** Reads the settings files and environment variables that decide where auto-compaction runs. */

import type { EngineInterface } from "claude-code";

import type { CompactionSetting } from "../types";
import { mergeSettings, parseLayer, resolveCompaction } from "./settings";

/** https://code.claude.com/docs/en/managed-settings */
const MANAGED_SETTINGS =
	"/Library/Application Support/ClaudeCode/managed-settings.json";

function nonEmpty(text: string | undefined): string | undefined {
	return text === undefined || text === "" ? undefined : text;
}

/** A file's text, or undefined where there is no path or the file cannot be read. */
async function readText(
	$: EngineInterface,
	path: string | undefined,
): Promise<string | undefined> {
	if (path === undefined) return undefined;
	return await $.fs.read(path).catch(() => undefined);
}

/**
 * Where auto-compaction runs for this session: the managed, local project,
 * project and user settings files merged in that precedence, and the
 * environment variables over them.
 *
 * Why: the user file sits under `CLAUDE_CONFIG_DIR`, else under `~/.claude`
 * (https://code.claude.com/docs/en/settings); a project's files sit under the
 * project root (https://code.claude.com/docs/en/settings#settings-files-and-who-they-affect).
 */
export async function readCompaction(
	$: EngineInterface,
): Promise<CompactionSetting> {
	const [
		configDir,
		home,
		window,
		percent,
		disableAutoCompact,
		disableCompact,
		root,
		model,
	] = await Promise.all([
		$.env.get("CLAUDE_CONFIG_DIR"),
		$.env.get("HOME"),
		$.env.get("CLAUDE_CODE_AUTO_COMPACT_WINDOW"),
		$.env.get("CLAUDE_AUTOCOMPACT_PCT_OVERRIDE"),
		$.env.get("DISABLE_AUTO_COMPACT"),
		$.env.get("DISABLE_COMPACT"),
		$.session.root().catch(() => undefined),
		$.session.model().catch(() => undefined),
	]);
	const userDir =
		nonEmpty(configDir) ?? (home === undefined ? undefined : `${home}/.claude`);
	const texts = await Promise.all([
		readText($, MANAGED_SETTINGS),
		readText($, root && `${root}/.claude/settings.local.json`),
		readText($, root && `${root}/.claude/settings.json`),
		readText($, userDir && `${userDir}/settings.json`),
	]);
	return resolveCompaction(mergeSettings(texts.map(parseLayer), model), {
		window,
		percent,
		disableAutoCompact,
		disableCompact,
	});
}
