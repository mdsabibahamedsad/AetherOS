import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  transpilePackages: ["@aetheros/shared", "@aetheros/config", "@aetheros/ui"],
  output: "standalone",
  poweredByHeader: false,
  reactStrictMode: true,
  eslint: {
    ignoreDuringBuilds: false,
  },
  typescript: {
    ignoreBuildErrors: false,
  },
  experimental: {
    optimizePackageImports: [
      "lucide-react",
      "@radix-ui/react-dialog",
      "@radix-ui/react-dropdown-menu",
      "@radix-ui/react-select",
      "@radix-ui/react-toast",
    ],
  },
};

export default nextConfig;
