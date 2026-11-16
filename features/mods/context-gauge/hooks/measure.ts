/** What one content block weighs: characters for text-like blocks, estimated tokens for media. */

/// <reference lib="esnext.typedarrays" />
import type { ApiContentBlock } from "claude-code";

import { PDF_TOKENS_PER_PAGE, PRIOR_TOKENS_PER_CHAR } from "./calibration";
import { parseModel, versionOf } from "./model-id";
import { isRecord } from "./record";

type Weight = { chars: number; media: number };

const NONE: Weight = { chars: 0, media: 0 };

/** Pixels per side of the square patch one image token covers. */
const IMAGE_PATCH = 28;

/** Image tokens the first model tier to see larger images caps at, and the cap before it. */
const IMAGE_CAP_LARGE = 4784;
const IMAGE_CAP_SMALL = 1568;

/** The first model version, 4.7, whose images may reach the larger cap. */
const LARGE_IMAGE_VERSION = 407;

/** Base64 characters read from an image's start, enough to reach a JPEG frame header behind its metadata segments. */
const IMAGE_HEAD_BASE64 = 262_144;

/** The bytes of `/Type` and of `/Page`, which a PDF page object carries and its page tree's `/Pages` also begins with. */
const PDF_TYPE: readonly number[] = [...("/Type" as string)].map((char) =>
	char.charCodeAt(0),
);
const PDF_PAGE: readonly number[] = [...("/Page" as string)].map((char) =>
	char.charCodeAt(0),
);

const JPEG_FRAMES: ReadonlySet<number> = new Set([
	0xc0, 0xc1, 0xc2, 0xc3, 0xc5, 0xc6, 0xc7, 0xc9, 0xca, 0xcb, 0xcd, 0xce, 0xcf,
]);

function jsonChars(value: unknown): number {
	return JSON.stringify(value)?.length ?? 0;
}

/** The characters of `value` where it is a string, else those of the whole `block` as JSON. */
function stringOrBlockChars(value: unknown, block: ApiContentBlock): Weight {
	return typeof value === "string"
		? chars(value.length)
		: chars(jsonChars(block));
}

function chars(count: number): Weight {
	return { chars: count, media: 0 };
}

function media(tokens: number): Weight {
	return { chars: 0, media: tokens };
}

function add(left: Weight, right: Weight): Weight {
	return {
		chars: left.chars + right.chars,
		media: left.media + right.media,
	};
}

function sum(weights: readonly Weight[]): Weight {
	return weights.reduce(add, NONE);
}

function imageCap(model: string): number {
	const parsed = parseModel(model);
	return parsed !== null && versionOf(parsed) >= LARGE_IMAGE_VERSION
		? IMAGE_CAP_LARGE
		: IMAGE_CAP_SMALL;
}

type Size = { width: number; height: number };

function ascii(bytes: Uint8Array, from: number, to: number): string {
	return String.fromCharCode(...bytes.subarray(from, to));
}

function view(bytes: Uint8Array): DataView {
	return new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
}

function uint24(data: DataView, at: number): number {
	return data.getUint16(at, true) + data.getUint8(at + 2) * 0x1_00_00;
}

function pngSize(bytes: Uint8Array): Size | null {
	if (bytes.length < 24 || ascii(bytes, 12, 16) !== "IHDR") return null;
	const data = view(bytes);
	return { width: data.getUint32(16), height: data.getUint32(20) };
}

function gifSize(bytes: Uint8Array): Size | null {
	if (bytes.length < 10) return null;
	const data = view(bytes);
	return { width: data.getUint16(6, true), height: data.getUint16(8, true) };
}

function jpegSize(bytes: Uint8Array): Size | null {
	const data = view(bytes);
	let at = 2;
	while (at + 9 <= bytes.length) {
		if (bytes[at] !== 0xff) return null;
		if (JPEG_FRAMES.has(data.getUint8(at + 1)))
			return {
				height: data.getUint16(at + 5),
				width: data.getUint16(at + 7),
			};
		at += 2 + data.getUint16(at + 2);
	}
	return null;
}

function webpSize(bytes: Uint8Array): Size | null {
	if (bytes.length < 30) return null;
	const data = view(bytes);
	const kind = ascii(bytes, 12, 16);
	if (kind === "VP8X")
		return { width: uint24(data, 24) + 1, height: uint24(data, 27) + 1 };
	if (kind === "VP8L") {
		const bits = data.getUint32(21, true);
		return {
			width: (bits & 0x3f_ff) + 1,
			height: ((bits >>> 14) & 0x3f_ff) + 1,
		};
	}
	if (kind === "VP8 ")
		return {
			width: data.getUint16(26, true) & 0x3f_ff,
			height: data.getUint16(28, true) & 0x3f_ff,
		};
	return null;
}

function imageSize(bytes: Uint8Array): Size | null {
	if (ascii(bytes, 1, 4) === "PNG") return pngSize(bytes);
	if (ascii(bytes, 0, 3) === "GIF") return gifSize(bytes);
	if (bytes[0] === 0xff && bytes[1] === 0xd8) return jpegSize(bytes);
	if (ascii(bytes, 0, 4) === "RIFF" && ascii(bytes, 8, 12) === "WEBP")
		return webpSize(bytes);
	return null;
}

function decode(data: string): Uint8Array | null {
	try {
		return Uint8Array.fromBase64(data);
	} catch {
		return null;
	}
}

function pdfPages(bytes: Uint8Array): number {
	let pages = 0;
	let at = bytes.indexOf(PDF_TYPE[0] ?? 0);
	while (at !== -1) {
		if (matchesAt(bytes, at, PDF_TYPE)) {
			let next = at + PDF_TYPE.length;
			while (isSpace(bytes[next])) next += 1;
			if (matchesAt(bytes, next, PDF_PAGE)) {
				const after = bytes[next + PDF_PAGE.length];
				if (after === undefined || !isLetter(after)) pages += 1;
			}
		}
		at = bytes.indexOf(PDF_TYPE[0] ?? 0, at + 1);
	}
	return pages;
}

function matchesAt(
	bytes: Uint8Array,
	at: number,
	pattern: readonly number[],
): boolean {
	return pattern.every((byte, index) => bytes[at + index] === byte);
}

function isSpace(byte: number | undefined): boolean {
	return byte === 0x20 || byte === 0x0a || byte === 0x0d || byte === 0x09;
}

function isLetter(byte: number): boolean {
	return (byte >= 0x41 && byte <= 0x5a) || (byte >= 0x61 && byte <= 0x7a);
}

function sourceData(block: ApiContentBlock): string | null {
	const { source } = block;
	if (!isRecord(source)) return null;
	const { type, data } = source;
	return type === "base64" && typeof data === "string" ? data : null;
}

function imageWeight(block: ApiContentBlock, model: string): Weight {
	const cap = imageCap(model);
	const data = sourceData(block);
	if (data === null) return media(cap);
	const head = decode(data.slice(0, IMAGE_HEAD_BASE64));
	const size = head === null ? null : imageSize(head);
	if (size === null || size.width === 0 || size.height === 0) return media(cap);
	const tokens =
		Math.ceil(size.width / IMAGE_PATCH) * Math.ceil(size.height / IMAGE_PATCH);
	return media(Math.min(tokens, cap));
}

function documentWeight(block: ApiContentBlock, model: string): Weight {
	const { source } = block;
	if (!isRecord(source)) return chars(jsonChars(block));
	const { type, data: text, content, media_type: mediaType } = source;
	if (type === "text" && typeof text === "string") return chars(text.length);
	if (type === "content") return contentWeight(content, model);
	const data = sourceData(block);
	if (data === null || mediaType !== "application/pdf")
		return chars(jsonChars(block));
	const body = decode(data);
	const pages = body === null ? 0 : pdfPages(body);
	return media(Math.max(1, pages) * PDF_TOKENS_PER_PAGE);
}

function contentWeight(content: unknown, model: string): Weight {
	if (typeof content === "string") return chars(content.length);
	if (!Array.isArray(content)) return NONE;
	return sum(
		content.map((item: unknown) => {
			if (!isRecord(item)) return chars(jsonChars(item));
			const { type } = item;
			return typeof type === "string"
				? weigh({ ...item, type }, model)
				: chars(jsonChars(item));
		}),
	);
}

function searchResultWeight(block: ApiContentBlock, model: string): Weight {
	const { title, source, content } = block;
	const heading =
		(typeof title === "string" ? title.length : 0) +
		(typeof source === "string" ? source.length : 0);
	return add(chars(heading), contentWeight(content, model));
}

function weigh(block: ApiContentBlock, model: string): Weight {
	const { type, text, name, input, thinking, content } = block;
	switch (type) {
		case "text":
			return stringOrBlockChars(text, block);
		case "tool_use":
		case "server_tool_use":
		case "mcp_tool_use":
			return typeof name === "string"
				? chars(name.length + jsonChars(input))
				: chars(jsonChars(block));
		case "tool_result":
			return contentWeight(content, model);
		case "image":
			return imageWeight(block, model);
		case "document":
			return documentWeight(block, model);
		case "search_result":
			return searchResultWeight(block, model);
		case "thinking":
			return stringOrBlockChars(thinking, block);
		case "redacted_thinking":
			return NONE;
		case "compaction":
			return stringOrBlockChars(content, block);
		default:
			return type.endsWith("_tool_result")
				? contentWeight(content, model)
				: chars(jsonChars(block));
	}
}

/** Characters of a text-like block, or estimated tokens of a media block; never 0 for a block with content. A block holding both, a tool result with an image and text, reports tokens, its text at the prior ratio. */
export function measureBlock(
	block: ApiContentBlock,
	model: string,
): { chars: number } | { media: number } {
	const weight = weigh(block, model);
	if (weight.media === 0) return { chars: weight.chars };
	return {
		media: weight.media + Math.ceil(weight.chars * PRIOR_TOKENS_PER_CHAR),
	};
}
