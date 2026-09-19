import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

// Gelistirmede API ayni kokenden gorunur (uretimde nginx.conf ayni isi yapar):
// CORS yok, istemci her zaman goreli yol kullanir.
const BACKEND = process.env.GRIDUP_BACKEND ?? "http://localhost:8000";

export default defineConfig({
  plugins: [react()],
  optimizeDeps: {
    include: [
      "echarts/core",
      "echarts/renderers",
      "echarts-gl/charts",
      "echarts-gl/components",
    ],
  },
  server: {
    port: 5173,
    proxy: {
      "/api/v1/stream": { target: BACKEND, ws: true },
      "/api": BACKEND,
      "/health": BACKEND,
    },
  },
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          three: ["three"],
        },
      },
    },
  },
  test: {
    environment: "node",
    include: ["src/**/*.test.ts"],
  },
});
