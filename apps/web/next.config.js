/** @type {import('next').NextConfig} */
const apiOrigin = (process.env.SMART_BI_API_ORIGIN || "http://127.0.0.1:8000").replace(/\/$/, "");

const nextConfig = {
  reactStrictMode: true,
  async rewrites() {
    return [
      {
        source: "/api-proxy/:path*",
        destination: `${apiOrigin}/:path*`
      }
    ];
  }
};

module.exports = nextConfig;
