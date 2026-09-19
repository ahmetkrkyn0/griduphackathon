import { describe, expect, it } from "vitest";
import type { PanelSummary } from "../api/types";
import { bakimVadesi, etkiEkseni, niceMax } from "./etki";

/**
 * F-21 — risk matrisinin ETKI ekseni.
 *
 * Kilitlenen iddia: matris kunye girildigi OLCUDE iki boyutludur. Kunye yoksa eski
 * (tek boyutlu) davranis AYNEN korunur; kismi kunyede eksik panolar gizlenmez.
 */

function panel(pano_id: string, abone_sayisi: number | null): PanelSummary {
  return {
    pano_id,
    name: pano_id,
    risk_score: 50,
    risk_mode: "HYP-NORMAL",
    top_alarm: null,
    top_prio: null,
    ttl_h: null,
    last_seen: "2026-09-18T09:00:00+00:00",
    comms_ok: true,
    abone_sayisi,
  };
}

describe("niceMax", () => {
  it("ekseni yuvarlak bir sayida bitirir", () => {
    expect(niceMax(1240)).toBe(1500);
    expect(niceMax(87)).toBe(90);
    expect(niceMax(412)).toBe(450);
  });

  it("bos/gecersiz girdide cokmez", () => {
    expect(niceMax(0)).toBe(1);
    expect(niceMax(-5)).toBe(1);
    expect(niceMax(Number.NaN)).toBe(1);
  });
});

describe("etkiEkseni", () => {
  it("hicbir kunye yoksa ESKI DAVRANIS korunur (y = risk skoru)", () => {
    const eksen = etkiEkseni([panel("A", null), panel("B", null)]);

    expect(eksen.mode).toBe(false);
    expect(eksen.max).toBe(100); // risk skoru olcegi
    expect(eksen.missing).toBe(0);
  });

  it("bos filoda da eski davranisa duser", () => {
    expect(etkiEkseni([]).mode).toBe(false);
  });

  it("tek bir kunye bile gercek etki eksenini acar", () => {
    const eksen = etkiEkseni([panel("A", 412), panel("B", null)]);

    expect(eksen.mode).toBe(true);
    expect(eksen.max).toBe(450);
  });

  it("kunyesiz panolar SAYILIR — gizlenmez", () => {
    const eksen = etkiEkseni([panel("A", 412), panel("B", null), panel("C", null)]);

    expect(eksen.missing).toBe(2);
  });

  it("olcek en buyuk abone sayisina gore kurulur", () => {
    const eksen = etkiEkseni([panel("A", 87), panel("B", 1240), panel("C", 233)]);

    expect(eksen.max).toBe(1500);
    expect(eksen.missing).toBe(0);
  });

  it("abone sayisi 0 olan pano kunyesiz SAYILMAZ (0 gecerli bir degerdir)", () => {
    // "Abonesi yok" ile "abone sayisini bilmiyoruz" ayni sey degildir: ilki olculmus
    // bir degerdir ve etki eksenine girer.
    const eksen = etkiEkseni([panel("A", 0), panel("B", 500)]);

    expect(eksen.missing).toBe(0);
    expect(eksen.mode).toBe(true);
  });
});

describe("bakimVadesi", () => {
  const now = Date.parse("2026-09-18T09:00:00+00:00");

  it("kunye yoksa rozet HIC cizilmez", () => {
    // Bos bir rozet "bakim gerekmiyor" gibi okunurdu; dogrusu hic gostermemek.
    expect(bakimVadesi(null, now)).toBeNull();
    expect(bakimVadesi(undefined, now)).toBeNull();
  });

  it("bozuk tarih rozet uretmez", () => {
    expect(bakimVadesi("bu bir tarih degil", now)).toBeNull();
  });

  it("gelecekteki vadeyi gun olarak sayar", () => {
    const vade = bakimVadesi("2026-10-18T09:00:00+00:00", now);

    expect(vade).toEqual({ gecti: false, gun: 30, metin: "Bakıma 30 gün" });
  });

  it("gecmis vadeyi GECTI olarak isaretler", () => {
    const vade = bakimVadesi("2026-08-19T09:00:00+00:00", now);

    expect(vade?.gecti).toBe(true);
    expect(vade?.gun).toBe(30);
    expect(vade?.metin).toBe("Bakım vadesi 30 gün geçti");
  });

  it("gun sayisi her zaman pozitiftir (isaret `gecti` alaninda tasinir)", () => {
    expect(bakimVadesi("2026-01-01T00:00:00+00:00", now)?.gun).toBeGreaterThan(0);
  });
});
