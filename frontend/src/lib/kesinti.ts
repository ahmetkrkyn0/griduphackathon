import type { OutageEvent } from "../api/types";

/**
 * Ust sebeke kesintisinin (F-22) arayuz yardimcilari.
 *
 * Saf fonksiyonlar olarak ayri duruyor cunku burada korunmasi gereken bir DURUSTLUK
 * kurali var: etkilenen abone sayisi BILINMIYORSA sifir gosterilmez. vitest bu depoda
 * `environment: "node"` ile calisir ve yalnizca `src/**\/*.test.ts` toplar; kurali bir
 * bilesenin JSX'ine gomseydik testle kilitleyemezdik.
 */

/** pano_id -> fider_id. Haritada kesintiye dahil panolari isaretlemek icin. */
export function kesintidekiPanolar(outages: readonly OutageEvent[]): Map<string, string> {
  const map = new Map<string, string>();
  for (const outage of outages) {
    for (const panel of outage.panolar) map.set(panel.pano_id, outage.fider_id);
  }
  return map;
}

export interface AboneOzeti {
  /** null = hicbir panonun kunyesi yok; SIFIR DEGIL. */
  toplam: number | null;
  /** Kunyesi olmadigi icin toplama giremeyen pano sayisi. */
  eksik: number;
  /** Ekranda gosterilecek metin. Bilinmiyorsa sayi DEGIL, "bilinmiyor" der. */
  metin: string;
}

/**
 * Etkilenen abone ozetini uretir (EPDK Madde 8/2 "etkilenen kullanici sayisi").
 *
 * Alan sunucuda hesaplanir; burada yalnizca GOSTERIM kurali var ve kural sudur:
 * toplam null ise sifir yazilmaz — "abone yok" ile "abone sayisini bilmiyoruz" ayni
 * sey degildir. Eksik pano sayisi da gizlenmez, cunku toplam o kadar eksiktir.
 */
export function aboneOzeti(outage: OutageEvent): AboneOzeti {
  const toplam = outage.abone_toplami ?? null;
  const eksik = outage.abone_eksik ?? 0;
  if (toplam === null) {
    return { toplam: null, eksik, metin: "bilinmiyor (künye içe aktarılmamış)" };
  }
  return {
    toplam,
    eksik,
    metin: eksik > 0 ? `${toplam} (${eksik} panonun künyesi yok)` : String(toplam),
  };
}
