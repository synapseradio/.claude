/** What a `claude-…` model id says of its model: family, and major and minor version. */

/** A model id read apart; the family is null where the id names none. */
export type ParsedModel = {
	family: string | null;
	major: number;
	minor: number;
};

/**
 * Where an id carries its version, with the family before it (`claude-opus-4-7`,
 * `claude-sonnet-5-5`) or after it (`claude-3-5-sonnet`). A date follows a
 * one-digit minor, so a two-digit group directly after the major, as in
 * `claude-opus-4-20250514`, is no minor.
 */
const MODEL_ID =
	/claude-(?:([a-z]+)-)?(\d+)(?:-(\d{1,2})(?!\d))?(?:-(opus|sonnet|haiku))?/u;

/** The family, major and minor an id names, or null where it names no version. */
export function parseModel(id: string): ParsedModel | null {
	const match = MODEL_ID.exec(id);
	if (match === null) return null;
	return {
		family: match[1] ?? match[4] ?? null,
		major: Number(match[2]),
		minor: Number(match[3] ?? 0),
	};
}

/** The version as one number, `major * 100 + minor`; a minor has at most two digits, so versions order as numbers. */
export function versionOf({ major, minor }: ParsedModel): number {
	return major * 100 + minor;
}
