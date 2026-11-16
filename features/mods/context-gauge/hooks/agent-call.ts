/** How a content block names a subagent's start: the Agent tool, and the id of a call to it. */

import type { ApiContentBlock } from "claude-code";

/** The tool that starts a subagent. */
export const AGENT_TOOL = "Agent";

/** The tool-use id of a block that calls the Agent tool, or null for any other block. */
export function agentCallId(block: ApiContentBlock): string | null {
	const { type, id, name } = block;
	return type === "tool_use" && name === AGENT_TOOL && typeof id === "string"
		? id
		: null;
}
