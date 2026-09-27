import type { NextConfig } from "next";
import path from "path";

const nextConfig: NextConfig = {
  turbopack: {
    // Evita que Turbopack tome C:\Users\Usuario como root por un package-lock ajeno
    root: path.resolve(__dirname),
  },
};

export default nextConfig;
