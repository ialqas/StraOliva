import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
  // `next dev` only: other hosts allowed to load the dev server, e.g. your LAN IP
  // for testing on a phone. Comma-separated in DEV_ORIGINS (frontend/.env.local).
  allowedDevOrigins: (process.env.DEV_ORIGINS ?? "").split(",").map((o) => o.trim()).filter(Boolean),
};

export default nextConfig;
