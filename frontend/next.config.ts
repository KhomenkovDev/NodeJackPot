import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Emit a self-contained `.next/standalone` build that includes a minimal
  // server.js with all required node_modules traced — required for the
  // multi-stage Docker build used by Cloud Run.
  output: 'standalone',
  images: {
    remotePatterns: [
      {
        protocol: 'https',
        hostname: 'cryptologos.cc',
      },
    ],
  },
};

export default nextConfig;
