import type { NextConfig } from "next";
import path from "node:path";

const nextConfig: NextConfig = {
  // Pin the workspace root to the monorepo, not an unrelated lockfile
  // Next.js might find higher up in the home directory.
  turbopack: {
    root: path.join(__dirname, "..", ".."),
  },
  // Old IA (Section 17 of the original spec) redirected to the new 8-route
  // IA from the redesign brief — see docs/ui_architecture.md.
  async redirects() {
    return [
      { source: "/demo", destination: "/scenario-lab", permanent: true },
      { source: "/dashboard", destination: "/", permanent: true },
      { source: "/provider", destination: "/providers", permanent: true },
      { source: "/provider/cases/:id", destination: "/providers", permanent: true },
      { source: "/onboarding", destination: "/", permanent: true },
      { source: "/settings", destination: "/", permanent: true },
      { source: "/settings/integrations", destination: "/providers", permanent: true },
      // Package review/approval is now an inline modal on /interventions.
      { source: "/interventions/:id", destination: "/interventions", permanent: true },
      // Decision detail is now a selectable row + evidence panel on /audit.
      { source: "/audit/:id", destination: "/audit", permanent: true },
    ];
  },
  async rewrites() {
    const apiOrigin = process.env.RELIEF_API_URL;
    if (!apiOrigin) return [];
    return [
      {
        source: "/v1/:path*",
        destination: `${apiOrigin.replace(/\/$/, "")}/v1/:path*`,
      },
    ];
  },
};

export default nextConfig;
