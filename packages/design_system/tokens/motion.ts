/**
 * Motion tokens (Section 18). Every animated component must respect
 * `prefers-reduced-motion` (Sections 21.3, 27) — consumers should read
 * durations through `resolveMotionDuration` rather than the raw token so
 * reduced-motion users get near-instant transitions automatically.
 */
export const duration = {
  instant: "0ms",
  fast: "120ms",
  base: "200ms",
  slow: "360ms",
  timelineRecalculate: "480ms",
} as const;

export const easing = {
  standard: "cubic-bezier(0.2, 0, 0, 1)",
  decelerate: "cubic-bezier(0, 0, 0, 1)",
  accelerate: "cubic-bezier(0.3, 0, 1, 1)",
} as const;

export type DurationToken = keyof typeof duration;

/** Returns "0ms" when the user prefers reduced motion, otherwise the token value. */
export function resolveMotionDuration(token: DurationToken, prefersReducedMotion: boolean): string {
  return prefersReducedMotion ? "0ms" : duration[token];
}
