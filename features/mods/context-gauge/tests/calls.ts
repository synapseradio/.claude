/** Tool-use ids, Agent calls and task notifications the counting and drawing tests share, so a notification names the very call it reports on. */

import type { ApiContentBlock } from "claude-code";

export const AGENT_CALL = "toolu_01P5THiNbsHHVK5tH4sBmnmN";
export const BASH_CALL = "toolu_01Bash000000000000000000";

/** An Agent tool use, `id`, sending `prompt`. */
export function agentUse(id: string, prompt = "go"): ApiContentBlock {
	return { type: "tool_use", id, name: "Agent", input: { prompt } };
}

/** The text of a background task's notification naming the call `toolUseId`, padded to `chars` characters where it is shorter. */
export function notification(toolUseId: string, chars = 0): string {
	const body = `<task-notification>\n<task-id>a1b2</task-id>\n<tool-use-id>${toolUseId}</tool-use-id>\n<status>completed</status>\n</task-notification>`;
	return body.padEnd(chars, "x");
}
