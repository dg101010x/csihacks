/**
 * Typography tokens (Section 20).
 *
 * - Geist Sans for interface text.
 * - Geist Mono for money, dates, event identifiers, model versions, and
 *   audit information.
 * - Numbers use tabular figures where supported so values do not visually
 *   shift during timeline updates (fontVariantNumeric below).
 */
export const fontFamily = {
  sans: "var(--font-geist-sans), ui-sans-serif, system-ui, sans-serif",
  mono: "var(--font-geist-mono), ui-monospace, 'SF Mono', monospace",
} as const;

export type TypographyLevel =
  | "displayTitle"
  | "pageTitle"
  | "sectionTitle"
  | "cardTitle"
  | "body"
  | "supportingLabel"
  | "numericalMetric"
  | "auditMetadata";

interface TypographyStyle {
  fontFamily: string;
  fontSize: string;
  lineHeight: string;
  fontWeight: number;
  letterSpacing?: string;
  fontVariantNumeric?: string;
}

/** Typography hierarchy (Section 20): display, page, section, card, body,
 * supporting label, numerical metric, audit metadata. */
export const typography: Record<TypographyLevel, TypographyStyle> = {
  displayTitle: {
    fontFamily: fontFamily.sans,
    fontSize: "2.5rem",
    lineHeight: "1.1",
    fontWeight: 600,
    letterSpacing: "-0.02em",
  },
  pageTitle: {
    fontFamily: fontFamily.sans,
    fontSize: "1.75rem",
    lineHeight: "1.2",
    fontWeight: 600,
    letterSpacing: "-0.01em",
  },
  sectionTitle: {
    fontFamily: fontFamily.sans,
    fontSize: "1.25rem",
    lineHeight: "1.3",
    fontWeight: 600,
  },
  cardTitle: {
    fontFamily: fontFamily.sans,
    fontSize: "1rem",
    lineHeight: "1.4",
    fontWeight: 600,
  },
  body: {
    fontFamily: fontFamily.sans,
    fontSize: "0.9375rem",
    lineHeight: "1.5",
    fontWeight: 400,
  },
  supportingLabel: {
    fontFamily: fontFamily.sans,
    fontSize: "0.8125rem",
    lineHeight: "1.4",
    fontWeight: 500,
  },
  numericalMetric: {
    fontFamily: fontFamily.mono,
    fontSize: "1.5rem",
    lineHeight: "1.2",
    fontWeight: 600,
    fontVariantNumeric: "tabular-nums",
  },
  auditMetadata: {
    fontFamily: fontFamily.mono,
    fontSize: "0.75rem",
    lineHeight: "1.4",
    fontWeight: 400,
    fontVariantNumeric: "tabular-nums",
  },
};
