import type { Config } from "tailwindcss";
import { colors } from "./tokens/colors";
import { borderRadius } from "./tokens/borders";
import { elevation } from "./tokens/elevation";
import { duration } from "./tokens/motion";

/**
 * Shared Tailwind preset (Section 18). apps/web extends this rather than
 * redefining tokens locally, so the whole product draws from one palette.
 */
const preset: Partial<Config> = {
  darkMode: ["class", '[data-theme="dark"]'],
  theme: {
    extend: {
      colors: {
        "deep-ink": colors.deepInk,
        porcelain: colors.porcelain,
        "trust-blue": colors.trustBlue,
        "relief-mint": colors.reliefMint,
        "signal-amber": colors.signalAmber,
        "risk-coral": colors.riskCoral,
        slate: colors.slate,
        background: "var(--color-background)",
        foreground: "var(--color-foreground)",
        surface: "var(--color-surface)",
        border: "var(--color-border)",
        primary: {
          DEFAULT: "var(--color-primary)",
          foreground: "var(--color-primary-foreground)",
        },
        "muted-foreground": "var(--color-muted-foreground)",
        positive: "var(--color-positive)",
        caution: "var(--color-caution)",
        risk: "var(--color-risk)",
      },
      fontFamily: {
        sans: ["var(--font-geist-sans)", "ui-sans-serif", "system-ui", "sans-serif"],
        mono: ["var(--font-geist-mono)", "ui-monospace", "SF Mono", "monospace"],
      },
      borderRadius: {
        sm: borderRadius.sm,
        md: borderRadius.md,
        lg: borderRadius.lg,
        xl: borderRadius.xl,
      },
      boxShadow: {
        sm: elevation.sm,
        md: elevation.md,
        lg: elevation.lg,
        overlay: elevation.overlay,
      },
      transitionDuration: {
        fast: duration.fast,
        base: duration.base,
        slow: duration.slow,
        "timeline-recalculate": duration.timelineRecalculate,
      },
    },
  },
};

export default preset;
