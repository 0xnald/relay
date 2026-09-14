import type { NextConfig } from "next";

// The command center calls the Relay API through same-origin `/api/*` paths. In development the
// rewrite targets the local backend; in a hosted deployment set RELAY_API_ORIGIN to the public
// Relay API origin (for example https://relay-api.example.com) at build time.
const apiOrigin = (process.env.RELAY_API_ORIGIN ?? "http://127.0.0.1:8000").replace(/\/+$/, "");

const nextConfig: NextConfig = {
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${apiOrigin}/api/:path*` }];
  }
};

export default nextConfig;
