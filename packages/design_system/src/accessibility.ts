/**
 * Accessibility helpers (Section 18 item 9).
 *
 * Enforces "no outcome may rely on color alone" and "every status requires
 * text and an icon" (Section 19, rules 7-8) at the type level: callers must
 * supply both a label and an icon name for every status tone, and cannot
 * construct a status from color alone.
 */
export type StatusTone = "neutral" | "positive" | "caution" | "risk";

export interface StatusDescriptor {
  tone: StatusTone;
  /** Human-readable text — never omit, even when an icon is present. */
  label: string;
  /** Name of an icon from the product's icon set — never omit, even when text is present. */
  icon: string;
}

export function createStatusDescriptor(descriptor: StatusDescriptor): StatusDescriptor {
  if (!descriptor.label.trim()) {
    throw new Error("StatusDescriptor requires a non-empty label (Section 19, rule 8).");
  }
  if (!descriptor.icon.trim()) {
    throw new Error("StatusDescriptor requires an icon name (Section 19, rule 8).");
  }
  return descriptor;
}

/**
 * "Approval likelihood unavailable" placeholder (Section 21.4) — use instead
 * of inventing a percentage when evidence is unavailable.
 */
export const APPROVAL_PROBABILITY_UNAVAILABLE_LABEL = "Approval likelihood unavailable";

/** Reads the user's reduced-motion preference. SSR-safe (defaults to false). */
export function prefersReducedMotion(): boolean {
  if (typeof window === "undefined" || typeof window.matchMedia !== "function") return false;
  return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}
