import { defineConfig, devices } from "@playwright/test";

/**
 * K7 / 7.2 — "7 ekranda 0 konsol hatasi" iddiasinin TEZGAHI.
 *
 * Bu dosyadan once o cumle bir IDDIAYDI: sonuc dogru olabilir ama depodan yeniden
 * uretilemiyordu. Buradaki amac sayiyi savunmak degil, olcumu TEKRARLANABILIR kilmak.
 *
 * ── IKI KIP, IKI AYRI SONUC ────────────────────────────────────────────────────
 * Kip `GRIDUP_E2E_KIP` ile secilir; varsayilan "mock".
 *
 *  mock  (varsayilan) : `npm run dev:mock` (:5173) — bu spec Vite'i KENDISI kaldirir.
 *                       Veri src/api/mock.ts'ten gelir; backend, veritabani, broker
 *                       GEREKMEZ. `assets/ekran/` goruntuleri yalnizca bu kipte
 *                       uretilir; docs/16 §5 de goruntulerin ornek veri kipinde
 *                       alindigini zaten soyluyor.
 *  canli              : ZATEN AYAKTA olan yigina baglanir (:3000 nginx + :8000 API).
 *                       `webServer` BU KIPTE TANIMLANMAZ: spec konteyneri baslatmaz,
 *                       durdurmaz, tohumlamaz. scripts/seed_demo.py MUNHASIR bir
 *                       veritabani ister (seed_demo.py:336-340) ve yazicilar acikken
 *                       kirilir; testi ona bagimli yapmak, testi yigin bakim islerine
 *                       bagimli yapmak olurdu. Tohumlama AYRI bir hazirlik adimidir.
 *
 * Ayrim SART: :3000'deki konteyner MOCK DEGILDIR (Dockerfile:9 duz `npm run build`,
 * yani VITE_USE_MOCKS kapali). Iki kip ayrilmazsa "hangi sayiyi olctuk" sorusu
 * cevapsiz kalir — KALAN-EKSIKLER.md:34'teki "gercek API ile" tam olarak canli kiptir.
 *
 * Kosum:
 *   npx playwright test                         -> mock kipi (Vite'i kendi kaldirir)
 *   GRIDUP_E2E_KIP=canli npx playwright test    -> canli kip (yigin ONCEDEN ayakta olmali)
 */
const KIP = process.env.GRIDUP_E2E_KIP === "canli" ? "canli" : "mock";
const MOCK_URL = "http://127.0.0.1:5173";
const CANLI_URL = process.env.GRIDUP_E2E_URL ?? "http://127.0.0.1:3000";

/**
 * 1425 px UYDURULMUS BIR SAYI DEGIL: `assets/ekran/` altindaki mevcut 8 PNG'nin
 * TAMAMI 1425 px genisligindedir (olculdu). Viewport buna esitlenmezse yeni
 * goruntuler eski dosya adlariyla ama farkli olcekte uretilir ve docs/16 §5'teki
 * tablo kendi icinde tutarsizlasir. Yukseklik onemsiz: goruntuler `fullPage` alinir.
 */
export const EKRAN_GENISLIK = 1425;

export default defineConfig({
  // MUTLAKA "./e2e": frontend kokune birakilirsa Playwright `src` altindaki 16 vitest
  // dosyasini da toplamaya calisir ve `describe is not defined` ile patlar.
  testDir: "./e2e",
  // Goruntuler `assets/ekran/`e yazilir; iki isci ayni dosyayi ezebilirdi.
  workers: 1,
  // Yeniden deneme YOK ve bu bilincli: konsol hatasi SAYAN bir testte retry,
  // kararsiz bir hatayi "gecti" diye gizler. Kararsizlik gorulmeli, yutulmamali.
  retries: 0,
  reporter: [["list"]],
  projects: [
    {
      name: KIP,
      use: {
        ...devices["Desktop Chrome"],
        baseURL: KIP === "canli" ? CANLI_URL : MOCK_URL,
        locale: "tr-TR",
        timezoneId: "Europe/Istanbul",
        // SIRA ONEMLI: `devices["Desktop Chrome"]` kendi viewport'unu (1280x720)
        // tasir; 1425 SPREAD'DEN SONRA yazilmazsa sessizce ezilir ve goruntuler
        // mevcut 8 PNG'den farkli olcekte cikar.
        viewport: { width: EKRAN_GENISLIK, height: 900 },
      },
    },
  ],
  // webServer yalnizca mock kipinde; canli kipte yigini spec YONETMEZ.
  ...(KIP === "mock"
    ? {
        webServer: {
          // dev:mock -> VITE_USE_MOCKS=1 yalnizca bu kipte acilir (api/client.ts:6).
          command: "npm run dev:mock -- --host 127.0.0.1 --port 5173 --strictPort",
          url: MOCK_URL,
          reuseExistingServer: !process.env.CI,
          timeout: 120_000,
        },
      }
    : {}),
});
