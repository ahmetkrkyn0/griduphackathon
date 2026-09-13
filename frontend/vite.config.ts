import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

// Gelistirmede API ayni kokenden gorunur (uretimde nginx.conf ayni isi yapar):
// CORS yok, istemci her zaman goreli yol kullanir.
const BACKEND = process.env.GRIDUP_BACKEND ?? "http://localhost:8000";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api/v1/stream": { target: BACKEND, ws: true },
      "/api": BACKEND,
      "/health": BACKEND,
    },
  },
  test: {
    environment: "node",
    include: ["src/**/*.test.ts"],
  },
});
