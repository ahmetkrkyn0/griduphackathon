import { describe, expect, it } from "vitest";
import type { OutageEvent } from "../api/types";
import { aboneOzeti, epdkDeger, kesintidekiPanolar, taslakMi } from "./kesinti";

/**
 * F-22 — kesinti gosteriminin durustluk kurali.
 *
 * Kilitlenen iddia: etkilenen abone sayisi BILINMIYORSA sifir gosterilmez ve kac panonun
 * sayilamadigi gizlenmez.
 */

function outage(over: Partial<OutageEvent> = {}): OutageEvent {
  return {
    outage_id: "OUT-F-1-20260918T0900Z",
    fider_id: "F-1",
    started_at: "2026-09-18T09:00:00+00:00",
    detected_at: "2026-09-18T09:05:00+00:00",
    ended_at: null,
    state: "acik",
    panolar: [
      { pano_id: "A", last_rx: "2026-09-18T09:00:00+00:00", abone_sayisi: 100 },
      { pano_id: "B", last_rx: "2026-09-18T09:00:00+00:00", abone_sayisi: null },
    ],
    ...over,
  };
}

describe("kesintidekiPanolar", () => {
  it("pano -> fider eslemesi cikarir", () => {
    const map = kesintidekiPanolar([outage()]);

    expect(map.get("A")).toBe("F-1");
    expect(map.get("B")).toBe("F-1");
    expect(map.has("C")).toBe(false);
  });

  it("kesinti yoksa bos harita doner", () => {
    expect(kesintidekiPanolar([]).size).toBe(0);
  });
});

describe("aboneOzeti", () => {
  it("bilinen aboneleri toplar ve EKSIGI soyler", () => {
    const ozet = aboneOzeti(outage({ abone_toplami: 100, abone_eksik: 1 }));

    expect(ozet.toplam).toBe(100);
    expect(ozet.eksik).toBe(1);
    expect(ozet.metin).toBe("100 (1 panonun künyesi yok)");
  });

  it("hicbir kunye yoksa SIFIR YAZMAZ", () => {
    // Asil kilit: "abone yok" ile "abone sayisini bilmiyoruz" ayni sey degildir.
    const ozet = aboneOzeti(outage({ abone_toplami: null, abone_eksik: 2 }));

    expect(ozet.toplam).toBeNull();
    expect(ozet.metin).not.toContain("0");
    expect(ozet.metin).toContain("bilinmiyor");
  });

  it("hepsinin kunyesi varsa eksik notu eklenmez", () => {
    const ozet = aboneOzeti(outage({ abone_toplami: 500, abone_eksik: 0 }));

    expect(ozet.metin).toBe("500");
  });
});

describe("epdkDeger", () => {
  it("olculen degeri oldugu gibi gosterir", () => {
    expect(epdkDeger(1327)).toBe("1327");
    expect(epdkDeger("Plansiz (ust sebeke)")).toBe("Plansiz (ust sebeke)");
  });

  it("olcmedigimiz alana SIFIR YAZMAZ", () => {
    // Asil kilit: 0 yazmak, olcmedigimiz bir alani "olculdu ve sifir cikti" gibi gosterirdi.
    expect(epdkDeger(null)).toBe("—");
    expect(epdkDeger(null)).not.toBe("0");
  });

  it("degeri 0 OLAN alani gizlemez", () => {
    // 0 gecerli bir olcumdur ve tireye cevrilmemeli.
    expect(epdkDeger(0)).toBe("0");
  });
});

describe("taslakMi", () => {
  it("taslak bayragini dogrular", () => {
    expect(taslakMi({ taslak: true })).toBe(true);
    expect(taslakMi({ taslak: false })).toBe(false);
    expect(taslakMi({})).toBe(false);
  });
});
