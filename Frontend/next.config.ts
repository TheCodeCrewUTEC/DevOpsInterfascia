import type { NextConfig } from "next";
import path from "path";

module.exports = {
  allowedDevOrigins: ['127.0.0.1'],
}

const nextConfig: NextConfig = {
  turbopack: {
    // Evita que Turbopack tome C:\Users\Usuario como root por un package-lock ajeno
    root: path.resolve(__dirname),
  },
};

export default nextConfig;
