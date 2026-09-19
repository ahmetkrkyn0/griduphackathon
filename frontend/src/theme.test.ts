import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";

/**
 * K7 / 7.3 — kontrast orani ARTIK DOKUMANDA DEGIL BURADA.
 *
 * NEDEN: `docs/16` §4 orani elle hesaplayip metne yazmisti ve 19 Eylul'de eskidigi
 * OLCULDU — dokumandaki `--ink #1f2224` / `--bg #ffffff` (~16:1) ciftinin ikisi de
 * artik theme.css'te yok. Metne yazilan sayi sessizce yanlislanir; test yanlislanamaz.
 *
 * BU TESTIN SINIRI — dogru okunmasi onemli: burada olculen sey TOKEN MATEMATIGIDIR,
 * ekranin kendisi degil. Gercekte cizilen zemin token olmayabilir: e2e/smoke.spec.ts
 * axe ile olctu ve `/bolge`deki `.kesinti-serit` zemininin `--bg` DEGIL #ebecee
 * oldugunu, ayni `--dim` token'inin orada 4,61:1 degil 4,21:1 verdigini gosterdi.
 * Yani bu test GEREKLI ama YETERLI degildir; ikisi birlikte okunur.
 *
 * Ortam "node" (vite.config.ts): print.test.ts ve labels.test.ts ile ayni desen —
 * kaynak dosyanin METNI okunur, DOM gerekmez.
 */
const themeCss = readFileSync(new URL("./theme.css", import.meta.url), "utf8");

/** `:root` blogundan bir CSS degiskeninin degerini okur. */
function token(ad: string): string {
  const m = themeCss.match(new RegExp(`--${ad}:\\s*([^;]+);`));
  if (!m) throw new Error(`theme.css icinde --${ad} bulunamadi`);
  return m[1].trim();
}

/** WCAG 2.1 bagil parlaklik (§ Relative luminance). */
function parlaklik(hex: string): number {
  let h = hex.replace("#", "");
  if (h.length === 3) h = [...h].map((c) => c + c).join("");
  const kanal = [0, 2, 4].map((i) => {
    const c = parseInt(h.slice(i, i + 2), 16) / 255;
    return c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
  });
  return 0.2126 * kanal[0] + 0.7152 * kanal[1] + 0.0722 * kanal[2];
}

/** WCAG 2.1 kontrast orani. */
function oran(on: string, arka: string): number {
  const [a, b] = [parlaklik(on), parlaklik(arka)];
  return (Math.max(a, b) + 0.05) / (Math.min(a, b) + 0.05);
}

// WCAG 2.1 AA: normal govde metni 4,5:1; buyuk metin (>=18,66 px kalin veya >=24 px) 3:1.
const AA_GOVDE = 4.5;

describe("theme.css kontrast — olculen, yazilan degil", () => {
  it("token degerleri dokumandaki degerlerle AYNI (degisirse docs/16 §4 da guncellenmeli)", () => {
    // Bu uc satir bir kilit: token degisirse test duser ve degisen sayinin
    // `docs/16` §4'e de tasinmasi ZORUNLU olur. Sessiz bayatlama boyle biter.
    expect(token("bg")).toBe("#f5f6f8");
    expect(token("ink")).toBe("#202b34");
    expect(token("dim")).toBe("#65717d");
  });

  it("govde metni (--ink / --bg) 13,33:1 — AA esiginin cok ustunde", () => {
    // 19 Eylul olcumu. docs/16 §4 bu satiri "~16:1" diyordu; o oran ESKI
    // (#1f2224 / #ffffff) token ciftinin degeriydi ve bugun hicbir yerde yok.
    expect(oran(token("ink"), token("bg"))).toBeCloseTo(13.33, 2);
  });

  it("ikincil metin (--dim / --bg) 4,61:1 — AA'yi yalnizca 0,11 ile geciyor", () => {
    // BU SAYI BIR UYARIDIR, bir basari degil. docs/16 §4 burada "~5,8:1" diyordu;
    // o da eski `--dim` (#5f666b) degeriydi. Marj 1,30x'ten 1,02x'e indi, yani
    // `--dim` bir tik daha acilirsa AA'nin ALTINA duser. Test o ani yakalar.
    const d = oran(token("dim"), token("bg"));
    expect(d).toBeCloseTo(4.61, 2);
    expect(d).toBeGreaterThan(AA_GOVDE);
  });

  it("oncelik rozetlerinin GERCEK renk ciftleri — olculen, varsayilan degil", () => {
    // BU TEST ONCE YANLIS YAZILDI ve olcum onu yanlisladi; dusturu odur.
    // Ilk hali "--p1/--p2/--p3 beyaz zeminde metin olarak AA'yi gecer" diyordu.
    // app.css:86-92 okununca gorulen GERCEK ciftler bambaska:
    //   .prio       -> color: #fff  (taban; rozet METNI beyaz)
    //   .prio-P1    -> background: var(--p1)
    //   .prio-P2    -> background: var(--p2)
    //   .prio-P3    -> background: var(--p3) AMA color: var(--ink) ile EZIYOR
    // Yani "--p3 beyaz zeminde metin" diye bir sey arayuzde HIC YOK.
    const beyaz = "#ffffff";
    expect(oran(beyaz, token("p1"))).toBeCloseTo(5.64, 2);
    expect(oran(beyaz, token("p2"))).toBeCloseTo(4.53, 2);
    expect(oran(token("ink"), token("p3"))).toBeCloseTo(3.67, 2);
  });

  it("P3 rozeti 4,5:1 esiginin ALTINDA — gizlenmiyor, kayit altinda", () => {
    // OLCULEN: --ink / --p3 = 3,67:1. `.prio` yazi tipi `700 14px` (app.css:86),
    // yani WCAG'in "buyuk metin" muafiyetine (>=18,66 px kalin) GIRMEZ; gereken esik
    // 4,5:1'dir ve saglanmiyor.
    //
    // OLCUM BOSLUGU — durustce: e2e/smoke.spec.ts'teki axe taramasi bu dugumu HIC
    // DEGERLENDIRMEDI, cunku taranan yedi ekranin hicbirinde P3 rozeti cizilmedi
    // (olculdu: /alarmlar'da tek `.prio` dugumu vardi ve P1'di, axe onu GECTI —
    // beyaz/`--p1` 5,64:1). Yani "axe 0 kontrast ihlali buldu" cumlesi bu rozeti
    // KAPSAMAZ. Burada kilitlenmesinin sebebi tam olarak budur.
    //
    // HAFIFLETICI (bir gecerlilik gerekcesi DEGIL): PrioMark.tsx:17 rozeti
    // `role="img"` + `aria-label` ile cizer ve oncelik renk + SEKIL + KARAKTER ile
    // birlikte kodlanir (ISA-101), yani bilgi yalnizca bu karakterin okunabilirligine
    // bagli degildir. Yine de oran esigin altindadir ve oyle yaziliyor.
    expect(oran(token("ink"), token("p3"))).toBeLessThan(AA_GOVDE);
  });
});
