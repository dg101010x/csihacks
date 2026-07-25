import { colors } from "./colors";

/**
 * Chart tokens (Section 18), mapped onto the timeline's semantic surfaces
 * (Section 21.3, 23). Risk Coral is reserved for verified/strongly
 * projected risk only (Section 19, rule 6) — never used decoratively.
 */
export const chartTokens = {
  baselineTrajectory: colors.slate,
  modifiedTrajectory: colors.trustBlue,
  uncertaintyBand: "rgba(49, 94, 251, 0.12)", // trustBlue at low opacity
  reserveLine: colors.deepInk,
  riskRegion: "rgba(217, 92, 92, 0.14)", // riskCoral at low opacity
  riskRegionBorder: colors.riskCoral,
  improvementMarker: colors.reliefMint,
  uncertaintyMarker: colors.signalAmber,
  gridLine: "#E4E7EC",
  axisLabel: colors.slate,
} as const;

export type ChartToken = keyof typeof chartTokens;
