import { defineConfig, devices } from "@playwright/test";

/**
 * K7 / 7.2 — "7 ekranda 0 konsol hatasi" iddiasinin TEZGAHI.
 *
 * Bu dosya iki dalin birlesimidir. main tarafi olcum tezgahini (mock/canli kipi,
 * 1425 px goruntu boru hatti, retry YOK) getirdi; berke/upgrade tarafi sanayi
 * arayuzu spec'lerini (industrial + twin) getirdi. Ikisi tek bir `use` blogunu
 * paylasamaz — cozum Playwright'in `projects` dizisidir: her spec kumesi kendi
 * viewport'u ve zaman asimiyla kosar, hicbir ayar feda edilmez.
 *
 * ── IKI KIP ───────────────────────────────────────────────────────────────────
 * Kip `GRIDUP_E2E_KIP` ile secilir; varsayilan "mock".
 *
 *  mock  (varsayilan) : `npm run dev:mock` (:5173) — bu config Vite'i KENDISI kaldirir.
 *                       Veri src/api/mock.ts'ten gelir; backend, veritabani, broker
 *                       GEREKMEZ. `assets/ekran/` goruntuleri yalnizca bu kipte uretilir.
 *  canli              : ZATEN AYAKTA olan yigina baglanir (:3000 nginx + :8000 API).
 *                       `webServer` BU KIPTE TANIMLANMAZ: spec konteyneri baslatmaz,
 *                       durdurmaz, tohumlamaz. scripts/seed_demo.py MUNHASIR bir
 *                       veritabani ister ve yazicilar acikken kirilir; testi ona
 *                       bagimli yapmak, testi yigin bakim islerine bagimli yapardi.
 *
 * Kosum:
 *   npm run e2e                                  -> mock kipi, HER IKI proje
 *   npx playwright test --project=sanayi         -> yalnizca sanayi spec'leri
 *   GRIDUP_E2E_KANAL=msedge npm run e2e          -> berke'nin Edge ortami
 *   GRIDUP_E2E_KIP=canli npm run e2e             -> yalnizca 7 ekran + axe
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

/**
 * berke'nin makinesinde Edge kanali kullanilmisti. Kanal ZORUNLU DEGIL: bos
 * birakilirsa paket ici Chromium kosar, yani CI'da ek kurulum istemez. Berke'nin
 * ortamini birebir tekrarlamak icin GRIDUP_E2E_KANAL=msedge verilir.
 */
const SANAYI_KANALI = process.env.GRIDUP_E2E_KANAL;

const ORTAK = { locale: "tr-TR", timezoneId: "Europe/Istanbul" } as const;

/** 7 ekran + axe erisilebilirlik kontrolu: kipe gore mock ya da canli. */
const ekranProjesi = {
  name: KIP,
  testMatch: /smoke\.spec\.ts$/,
  use: {
    ...devices["Desktop Chrome"],
    ...ORTAK,
    baseURL: KIP === "canli" ? CANLI_URL : MOCK_URL,
    // SIRA ONEMLI: `devices["Desktop Chrome"]` kendi viewport'unu (1280x720) tasir;
    // 1425 SPREAD'DEN SONRA yazilmazsa sessizce ezilir ve goruntuler mevcut 8
    // PNG'den farkli olcekte cikar.
    viewport: { width: EKRAN_GENISLIK, height: 900 },
  },
};

/**
 * Sanayi arayuzu (industrial + twin): SABIT ornek-veri kimlikleri ve sabit satir
 * sayilari iddia eder, o yuzden YALNIZCA mock kipinde anlamlidir. baseURL kosulsuz
 * MOCK_URL: biri elle `--project=sanayi` derse bile canli yigina yonelmez.
 */
const sanayiProjesi = {
  name: "sanayi",
  testMatch: /(industrial|twin)\.spec\.ts$/,
  // 45_000 IDI ve twin.spec.ts'i DUSURUYORDU. Teshis (20 Eylul): testin kendisi
  // saglam — 390 px'e inip 3D ikizi yeniden baglamak izole kosumda canvas'i
  // sorunsuz getiriyor (.twin-workbench canvas = 1, pageerror = 0). Dusme sebebi
  // SURE: spec ~20 etkilesim + iki tam ekran gecisi + WebGL sahnesi tasiyor ve
  // olculen kosum suresi bu makinede 1,5 DAKIKA. 45 sn'nin marji yoktu; testin
  // SON beklentisi, saatin bittigi yerde patliyordu. Dogru duzeltme testi kismak
  // degil, butceyi olculen sureye gore acmaktir — 150 sn ~1,7x marj birakir.
  // retries HALA 0: bu bir kararsizligi gizleme degil, yanlis bir zaman asiminin
  // duzeltilmesidir.
  timeout: 150_000,
  use: {
    ...devices["Desktop Chrome"],
    ...ORTAK,
    ...(SANAYI_KANALI ? { channel: SANAYI_KANALI } : {}),
    baseURL: MOCK_URL,
    viewport: { width: 1440, height: 1000 },
    trace: "retain-on-failure" as const,
  },
};

export default defineConfig({
  // MUTLAKA "./e2e": frontend kokune birakilirsa Playwright `src` altindaki vitest
  // dosyalarini da toplamaya calisir ve `describe is not defined` ile patlar.
  testDir: "./e2e",
  fullyParallel: false,
  // Goruntuler `assets/ekran/`e yazilir; iki isci ayni dosyayi ezebilirdi.
  workers: 1,
  // Yeniden deneme YOK ve bu bilincli: konsol hatasi SAYAN bir testte retry,
  // kararsiz bir hatayi "gecti" diye gizler. Kararsizlik gorulmeli, yutulmamali.
  retries: 0,
  reporter: [["list"]],
  // Canli kipte sanayi projesi listeye HIC girmez: mock.ts kimliklerine dayaniyor.
  projects: KIP === "canli" ? [ekranProjesi] : [ekranProjesi, sanayiProjesi],
  // webServer yalnizca mock kipinde; canli kipte yigini config YONETMEZ.
  ...(KIP === "mock"
    ? {
        webServer: {
          // dev:mock -> VITE_USE_MOCKS=1 yalnizca bu kipte acilir (api/client.ts).
          command: "npm run dev:mock -- --host 127.0.0.1 --port 5173 --strictPort",
          url: MOCK_URL,
          reuseExistingServer: !process.env.CI,
          timeout: 120_000,
        },
      }
    : {}),
});
