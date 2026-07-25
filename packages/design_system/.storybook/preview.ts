import type { Preview } from "@storybook/react";
import "../tokens.css";
import "./storybook.css";

const preview: Preview = {
  parameters: {
    controls: { matchers: { color: /(background|color)$/i, date: /Date$/i } },
    backgrounds: {
      default: "porcelain",
      values: [
        { name: "porcelain", value: "#F7F8F5" },
        { name: "deep-ink", value: "#0B1220" },
      ],
    },
    a11y: { test: "error" },
  },
};

export default preview;
