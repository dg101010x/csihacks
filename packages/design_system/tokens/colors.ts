/**
 * Color tokens (Section 19). Exact hex values from the spec — do not adjust
 * without updating this file's usage rules and the spec together.
 *
 * Usage rules (enforced by convention, not by the type system — see
 * accessibility helpers in ../src/status.ts for the "text + icon" rule):
 *
 * 1. Deep Ink is used for navigation, primary text, and enterprise surfaces.
 * 2. Porcelain is used for the primary background.
 * 3. Trust Blue is used for selected controls and primary actions.
 * 4. Relief Mint is used for confirmed improvement.
 * 5. Signal Amber is used for upcoming uncertainty.
 * 6. Risk Coral is used only for verified or strongly projected risk.
 * 7. No outcome may rely on color alone.
 * 8. Every status requires text and an icon.
 * 9. Risk Coral must not dominate entire screens.
 * 10. The design must not imitate Wells Fargo's red and gold identity.
 */
export const colors = {
  deepInk: "#0B1220",
  porcelain: "#F7F8F5",
  trustBlue: "#315EFB",
  reliefMint: "#24B99A",
  signalAmber: "#E9A93B",
  riskCoral: "#D95C5C",
  slate: "#667085",
} as const;

export type ColorToken = keyof typeof colors;

/** Semantic aliases — prefer these over raw color names in product code. */
export const semanticColors = {
  background: colors.porcelain,
  foreground: colors.deepInk,
  surface: "#FFFFFF",
  border: "#E4E7EC",
  primary: colors.trustBlue,
  primaryForeground: "#FFFFFF",
  muted: colors.slate,
  positive: colors.reliefMint,
  caution: colors.signalAmber,
  risk: colors.riskCoral,
} as const;

export type SemanticColorToken = keyof typeof semanticColors;
