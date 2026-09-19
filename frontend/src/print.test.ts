import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";

// SINIR: yazdirma ciktisinin KENDISI burada dogrulanamaz. Bu dosya "node" ortaminda
// kosar (vite.config.ts) ve kaynak dosyalarin METNINI okur; sayfa duzeni uretmez.
//
// 19 Eylul duzeltmesi: bu yorum eskiden "DOM yok" ve "yeni npm bagimliligi yasak"
// diyordu. K7/7.1-7.2 ile IKISI DE ARTIK YANLIS — depoda jsdom, @testing-library/react
// ve Playwright var; `.tsx` bilesen testleri jsdom'da kosuyor.
// Gercek sinir bundan DAR ve degismedi: jsdom sayfa duzeni hesaplamaz ve `@page` /
// `@media print` kurallarini UYGULAMAZ, yani kagit ciktisi jsdom'da da olculemez.
// Playwright ile olculebilirdi (`page.pdf()` yalnizca Chromium'da calisir); bu bilincli
// olarak YAPILMADI ve K7'de bir OLCUM BOSLUGU olarak kayitlidir.
//
// Bu test yalnizca sozlesmeyi korur: yazdirma kurallari tek dosyada durur, Kara kutu
// ekrani onu yukler ve raporun gerektirdigi bloklar (imza, ibare, iki zaman damgasi,
// 2B on gorunus) ekrandan silinmez. Kagit ciktisinin gorsel dogrulamasi elle yapilir.
const printCss = readFileSync(new URL("./print.css", import.meta.url), "utf8");
const appCss = readFileSync(new URL("./app.css", import.meta.url), "utf8");
const themeCss = readFileSync(new URL("./theme.css", import.meta.url), "utf8");
const olayAnalizi = readFileSync(new URL("./pages/OlayAnalizi.tsx", import.meta.url), "utf8");

describe("print.css", () => {
  it("A4 dikey sayfa tanimi var", () => {
    expect(printCss).toMatch(/@page\s*\{[^}]*size:\s*A4 portrait/);
  });

  it("yazdirma kurallari tek bir @media print blogunda toplanmis", () => {
    expect(printCss.match(/@media print/g)).toHaveLength(1);
    expect(appCss).not.toContain("@media print");
    expect(themeCss).not.toContain("@media print");
  });

  it("gezinme, durum seridi ve etkilesim ogeleri kagitta gizlenir", () => {
    for (const selector of [".topbar", ".strip", ".back", ".bb-bar"]) {
      expect(printCss).toContain(selector);
    }
  });

  it("ekranda gizli bloklar yalnizca kagitta acilir", () => {
    expect(printCss).toMatch(/\.print-only\s*\{\s*display:\s*none/);
    expect(printCss).toContain(".report .print-head");
    expect(printCss).toContain(".report .print-sign");
  });

  it("rapor duzeni yalnizca olay ekranina (.report) baglanmis", () => {
    // Diger alti ekranin cikti duzeni bu dosyadan etkilenmemeli.
    const scoped = [".back", ".bb-bar", ".ident", ".statement", ".split", ".timeline", ".front"];
    for (const selector of scoped) expect(printCss).toContain(`.report ${selector}`);
  });

  it("sayfa bolunmesi imza ve grafik bloklarini ortadan kesmez", () => {
    expect(printCss.match(/break-inside:\s*avoid/g)?.length ?? 0).toBeGreaterThanOrEqual(4);
  });
});

describe("OlayAnalizi yazdirma yolu", () => {
  it("print.css'i yukler", () => expect(olayAnalizi).toContain('import "../print.css"'));

  it("tarayici yazdirmasini kullanir — yeni bagimlilik yok", () => {
    expect(olayAnalizi).toContain("window.print()");
  });

  it("rapor kapsayicisi ve yazdirma dugmesi var", () => {
    expect(olayAnalizi).toContain('className="page report"');
    expect(olayAnalizi).toContain("Olay raporunu yazdır");
  });

  it("3B ikiz yerine 2B on gorunus basilir", () => {
    expect(olayAnalizi).toContain("OnGorunus");
    expect(olayAnalizi).not.toContain("Ikiz3D");
  });

  it("ornek veri ibaresi api bayragindan turetilir", () => {
    expect(olayAnalizi).toContain("usingMocks");
    expect(olayAnalizi).toContain("ÖRNEK/SENTETİK VERİDEN ÜRETİLMİŞTİR");
  });

  it("hem olay hem alindi zaman damgasi basilir", () => {
    expect(olayAnalizi).toContain("Olay zamanı");
    expect(olayAnalizi).toContain("Rapor alındığı an");
    // Damga yazdirma penceresi acilmadan once tazelenir.
    expect(olayAnalizi).toContain("beforeprint");
    expect(olayAnalizi).toContain("flushSync");
  });

  it("uc imza satiri hazir", () => {
    expect(olayAnalizi).toContain("SIGN_ROLES");
    expect(olayAnalizi).toMatch(/const SIGN_ROLES = \[[^\]]*\] as const;/);
    expect(olayAnalizi.match(/"(Raporu hazırlayan|Kontrol eden \(vardiya amiri\)|Teslim alan)"/g)).toHaveLength(3);
  });

  it("F-02 ile gelen 336 saatlik pencere korunur", () => {
    expect(olayAnalizi).toContain("const WINDOWS = [24, 72, 168, 336] as const;");
  });
});
