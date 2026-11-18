import type { NextConfig } from 'next';

const isDev = process.env.NODE_ENV === 'development';
// Only used by the dev server. In production Nginx serves the static files and proxies /api.
const apiProxyTarget = process.env.API_PROXY_TARGET ?? 'http://localhost:4000';

const nextConfig: NextConfig = {
  // Static export: production has no Node process for the web app.
  output: 'export',
  images: { unoptimized: true },
  reactStrictMode: true,
  ...(isDev
    ? {
        async rewrites() {
          return [{ source: '/api/:path*', destination: `${apiProxyTarget}/api/:path*` }];
        },
      }
    : {}),
};

export default nextConfig;
