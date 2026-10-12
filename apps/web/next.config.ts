import type { NextConfig } from "next";

const isGitHubPages = process.env.GITHUB_PAGES === "true";

const nextConfig: NextConfig = {
  allowedDevOrigins: ["127.0.0.1"],
  assetPrefix: isGitHubPages ? "/FluxSG" : undefined,
  basePath: isGitHubPages ? "/FluxSG" : undefined,
  output: isGitHubPages ? "export" : "standalone",
  reactStrictMode: true,
  trailingSlash: isGitHubPages,
};

export default nextConfig;

