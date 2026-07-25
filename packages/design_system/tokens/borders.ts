/** Border tokens (Section 18). */
export const borderRadius = {
  none: "0px",
  sm: "6px",
  md: "10px",
  lg: "14px",
  xl: "20px",
  full: "9999px",
} as const;

export const borderWidth = {
  hairline: "1px",
  thick: "2px",
} as const;

export type BorderRadiusToken = keyof typeof borderRadius;
