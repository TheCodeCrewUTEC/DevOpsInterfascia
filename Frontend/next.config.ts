import type { NextConfig } from "next";
import path from "path";

// Cache-Control para el CDN (Cloudflare) y el navegador. Next ya marca /_next/static
// como inmutable; esto cubre los logos e imágenes de /public, que cambian muy poco.
const UN_DIA = 60 * 60 * 24;

const nextConfig: NextConfig = {
  allowedDevOrigins: ["127.0.0.1"],
  turbopack: {
    // Evita que Turbopack tome C:\Users\Usuario como root por un package-lock ajeno
    root: path.resolve(__dirname),
  },
  async headers() {
    return [
      {
        source: "/:archivo(.*\\.(?:png|jpg|jpeg|svg|webp|ico))",
        headers: [
          {
            key: "Cache-Control",
            value: `public, max-age=${UN_DIA}, s-maxage=${UN_DIA * 7}, stale-while-revalidate=${UN_DIA}`,
          },
        ],
      },
    ];
  },
};

export default nextConfig;
