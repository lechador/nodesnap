import type { NextConfig } from "next";

const API = process.env.NODESNAP_API ?? "http://localhost:8000";

const nextConfig: NextConfig = {
  async rewrites() {
    return [
      { source: "/api/v1/:path*", destination: `${API}/api/v1/:path*` },
      { source: "/artifacts/:path*", destination: `${API}/artifacts/:path*` },
      { source: "/health", destination: `${API}/health` },
    ];
  },
};

export default nextConfig;
