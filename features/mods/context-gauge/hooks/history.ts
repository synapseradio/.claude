/** What a resumed conversation weighs, read from the engine's messages in API form. */

import type { ApiContentBlock, ApiMessage } from "claude-code";

import type { HistoryRead } from "../types";
import { agentCallId } from "./agent-call";
import { measureBlock } from "./measure";

/** The engine returns at most this many messages; a read this long may have lost its start. */
const MESSAGE_LIMIT = 4096;

const FNV_OFFSET = 0x81_1c_9d_c5;
const FNV_PRIME = 0x01_00_01_93;

function fnv1a(text: string): string {
	let hash = FNV_OFFSET;
	for (let index = 0; index < text.length; index += 1) {
		hash = Math.imul(hash ^ text.charCodeAt(index), FNV_PRIME) >>> 0;
	}
	return hash.toString(16).padStart(8, "0");
}

function blockFingerprint(block: ApiContentBlock): string {
	const { type, id } = block;
	return type === "tool_use" && typeof id === "string"
		? id
		: fnv1a(JSON.stringify(block));
}

/** The fingerprint of a response's first block that is not thinking, or null where it has none. */
export function fingerprintOf(
	blocks: readonly ApiContentBlock[],
): string | null {
	const answer = blocks.find(
		({ type }) => type !== "thinking" && type !== "redacted_thinking",
	);
	return answer === undefined ? null : blockFingerprint(answer);
}

/** The figures of a conversation: characters and media tokens of every block, the Agent call ids, and the first answer's fingerprint. */
export function historyOf(
	messages: readonly ApiMessage[],
	model: string,
): HistoryRead {
	let chars = 0;
	let media = 0;
	let fingerprint: string | null = null;
	const agentCalls: string[] = [];
	for (const message of messages) {
		for (const block of message.content) {
			const weight = measureBlock(block, model);
			if ("chars" in weight) chars += weight.chars;
			else media += weight.media;
			const agentCall = agentCallId(block);
			if (agentCall !== null) agentCalls.push(agentCall);
		}
		if (fingerprint === null && message.role === "assistant") {
			fingerprint = fingerprintOf(message.content);
		}
	}
	return {
		chars,
		media,
		agentCalls,
		fingerprint,
		truncated: messages.length >= MESSAGE_LIMIT,
	};
}
