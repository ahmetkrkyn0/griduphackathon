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
    // Varsayilan ortam "node" KALIYOR ve bu bir olcumun sonucudur, tercih degil.
    // 19 Eylul'de global `environment: "jsdom"` denendi: 12 dosyanin 3'u KIRILDI
    // (print.test.ts 14 + labels.test.ts 16 + panelGeometry.test.ts 8 = 38 test),
    // cunku ucu de `readFileSync(new URL("...", import.meta.url))` ile kaynak/sozlesme
    // dosyasi okuyor ve jsdom'da import.meta.url "file:" semasinda degil
    // -> TypeError: The URL must be of scheme file. Sure de 1,95 s'den 40,02 s'ye cikti.
    environment: "node",
    // .tsx testleri DOM ister; yalnizca onlar jsdom'a girer, node testleri bedel odemez.
    environmentMatchGlobs: [["src/**/*.test.tsx", "jsdom"]],
    // `?(x)` SART. Onceki hali ["src/**/*.test.ts"] idi ve .tsx dosyalarini HIC TOPLAMIYORDU:
    // bilesen testi yazilir, `npm test` yine "136 passed" der ve YESIL gorunur — test ise
    // hic kosmamistir. Sessiz basarisizlik. Dogrulama olcutu: "Test Files" sayisi 12'den buyuk olmali.
    include: ["src/**/*.test.ts?(x)"],
    // jsdom'un eksik web API'leri (bugun yalnizca ResizeObserver). "node" testlerinde
    // dosya yuklenir ama kosulu saglanmaz, yani onlara hicbir bedeli yoktur.
    setupFiles: ["src/test/setup.ts"],
  },
});

