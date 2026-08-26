import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

const BACKEND = process.env.VITE_BACKEND_URL ?? "http://127.0.0.1:5000";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    // In development the SPA calls /api/v1 on its own origin and Vite forwards
    // it to Flask, which mirrors how the two are served in production.
    proxy: { "/api": { target: BACKEND, changeOrigin: true } },
  },
  build: { outDir: "dist", sourcemap: false },
  test: {
    environment: "jsdom",
    include: ["src/**/*.test.ts", "src/**/*.test.tsx"],
  },
});
