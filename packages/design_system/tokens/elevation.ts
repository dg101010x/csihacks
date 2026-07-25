/** Elevation tokens (Section 18). Soft, low-contrast shadows — the product
 * communicates state through text/icon/color per Section 19, not depth. */
export const elevation = {
  none: "none",
  sm: "0 1px 2px 0 rgb(11 18 32 / 0.04)",
  md: "0 2px 8px -2px rgb(11 18 32 / 0.08), 0 1px 2px -1px rgb(11 18 32 / 0.04)",
  lg: "0 8px 24px -4px rgb(11 18 32 / 0.12), 0 2px 6px -2px rgb(11 18 32 / 0.06)",
  overlay: "0 16px 48px -8px rgb(11 18 32 / 0.20)",
} as const;

export type ElevationToken = keyof typeof elevation;
