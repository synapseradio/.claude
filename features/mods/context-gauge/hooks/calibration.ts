/** Multiple of an interval's counted rows that its tokens may reach before the excess shows as reminders or gap. */
export const CEILING_FACTOR = 2;

/** Tokens per character assumed for text-like rows before a model has a measured ratio. */
export const PRIOR_TOKENS_PER_CHAR = 0.43;

/** Tokens below which the attribution gap is not drawn. */
export const GAP_FLOOR_TOKENS = 1500;

/** Share of message tokens below which the attribution gap is not drawn. */
export const GAP_FLOOR_SHARE = 0.02;

/** Tokens a PDF page is estimated to carry. */
export const PDF_TOKENS_PER_PAGE = 2250;

/** Characters an interval must hold before it adds to the pooled ratio. */
export const MIN_RATIO_INTERVAL_CHARS = 2000;
