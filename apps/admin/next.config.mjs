const coreApiUrl = process.env.CORE_API_URL || "http://127.0.0.1:8000";

/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  async rewrites() {
    return [
      {
        source: "/core/:path*",
        destination: `${coreApiUrl}/:path*`,
      },
    ];
  },
};

export default nextConfig;
