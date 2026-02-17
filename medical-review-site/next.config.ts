import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
  // Note: standalone output required by @netlify/plugin-nextjs
};

export default nextConfig;
