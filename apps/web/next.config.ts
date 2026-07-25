import type { NextConfig } from "next";
import path from "node:path";

const nextConfig: NextConfig = {
  // Pin the workspace root to the monorepo, not an unrelated lockfile
  // Next.js might find higher up in the home directory.
  turbopack: {
    root: path.join(__dirname, "..", ".."),
  },
};

export default nextConfig;
