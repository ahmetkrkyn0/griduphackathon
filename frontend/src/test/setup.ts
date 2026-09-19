/**
 * jsdom eksikleri (K7 / 7.1). vite.config.ts `setupFiles` ile yuklenir.
 *
 * NEDEN: jsdom `ResizeObserver` UYGULAMAZ, ama lib/useChartWidth.ts:13 onu kosulsuz
 * `new ResizeObserver(...)` ile cagirir. Grafik ciziyor olsun olmasin, useChartWidth
 * kullanan HER sayfa testi bu satirda "ResizeObserver is not defined" ile duserdi.
 *
 * NE OLCULMUYOR: bu koltuk degnegi HICBIR ZAMAN yeniden olcum tetiklemez (`callback`
 * cagrilmaz). Yani genislige BAGLI cizim davranisi burada test EDILMEZ; test edilen sey
 * bilesenin useChartWidth'in baslangic genisligiyle (560 px) cizilip cizilmedigidir.
 * Gercek yeniden boyutlama davranisi yalnizca e2e/smoke.spec.ts'te, gercek tarayicida olculur.
 */
if (typeof globalThis.ResizeObserver === "undefined") {
  globalThis.ResizeObserver = class {
    observe(): void {}
    unobserve(): void {}
    disconnect(): void {}
  } as unknown as typeof ResizeObserver;
}
