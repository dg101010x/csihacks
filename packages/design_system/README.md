# @relief/design-system

Color, typography, spacing, border, elevation, motion, and chart tokens plus
component primitives and accessibility helpers (Section 18).

- `tokens/` — framework-agnostic TS token objects (colors, typography, spacing,
  borders, elevation, motion, chart).
- `tokens.css` — the same tokens as CSS custom properties; `apps/web` imports
  this into `globals.css`.
- `tailwind-preset.ts` — Tailwind config preset extending `theme.colors` /
  `fontFamily` / `borderRadius` / `boxShadow` / `transitionDuration` from the
  tokens above. Consuming apps should use this preset rather than redefining
  the palette.
- `src/accessibility.ts` — `StatusDescriptor` (forces every status to carry
  both a label and an icon, Section 19 rules 7-8), `APPROVAL_PROBABILITY_UNAVAILABLE_LABEL`
  (Section 21.4), `prefersReducedMotion()`.
- `src/components/` — Phase A primitives (Button, form controls, Card system,
  status indicators, empty/loading states) with Storybook stories.

## Color rules (Section 19)

1. Deep Ink — navigation, primary text, enterprise surfaces.
2. Porcelain — primary background.
3. Trust Blue — selected controls, primary actions.
4. Relief Mint — confirmed improvement only.
5. Signal Amber — upcoming uncertainty only.
6. Risk Coral — verified or strongly projected risk only. Must never dominate
   a whole screen.
7. No outcome may rely on color alone — pair with text and an icon.
8. The palette must not imitate Wells Fargo's red/gold identity.

## Storybook

```bash
pnpm --filter @relief/design-system storybook       # dev, port 6006
pnpm --filter @relief/design-system build-storybook  # static build
```
