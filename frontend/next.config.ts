import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Run the dev server on port 3000 (default). The backend is expected on
  // another origin/port; the frontend connects directly via WebSocket so no
  // rewrites are needed.
  reactStrictMode: true,
};

export default nextConfig;
