import type { PanelSummary } from "../api/types";

/**
 * Risk matrisinin ETKI ekseni (F-21).
 *
 * Saf fonksiyon olarak ayri duruyor cunku asil karar burada: matris ne zaman gercekten
 * iki boyutlu olur, ne zaman eski (tek boyutlu) davranisina duser. Bu karari bir
 * bilesenin icine gomseydik kurali TEK BASINA sinayamazdik: bir bilesen testi matrisin
 * CIZILMIS halini gorur, karari degil.
 *
 * 19 Eylul notu: bu yorum eskiden "vitest `environment: node` ile calisir ve yalnizca
 * `src/**\/*.test.ts` toplar" diyordu; K7/7.1 ile ikisi de degisti — `include` artik
 * `src/**\/*.test.ts?(x)` ve `.tsx` testleri jsdom'da kosuyor (vite.config.ts
 * `environmentMatchGlobs`). Yani bugun bilesen testi YAZILABILIR; bu fonksiyonun ayri
 * durma gerekcesi bir ARAC kisiti degil, kararin gorunur olmasidir.
 */

/** Ekseni okunur bir yuvarlak sayida bitirir (1240 -> 1500). */
export function niceMax(value: number): number {
  if (!Number.isFinite(value) || value <= 0) return 1;
  const magnitude = 10 ** Math.floor(Math.log10(value));
  const step = magnitude / 2;
  return Math.ceil(value / step) * step;
}

export interface EtkiEkseni {
  /** true: y ekseni abone sayisi (gercek etki). false: eski davranis, y = risk skoru. */
  mode: boolean;
  /** Etki modunda eksenin ust siniri; degilse 100 (risk skoru olcegi). */
  max: number;
  /** Kunyesi ice aktarilmamis pano sayisi — GIZLENMEZ, altyazida yazilir. */
  missing: number;
}

/**
 * Filoda EN AZ BIR panonun abone sayisi biliniyorsa etki modu acilir.
 *
 * NEDEN "en az bir" ve "hepsi" degil: kismi kunye de gercek bir etki ekseni verir ve
 * gercek kurulumda kutuk hicbir zaman %100 dolu olmaz. Kunyesi olmayan panolar
 * GIZLENMEZ; cagiran onlari ayri bir seritte cizer ve y=0'a KOYMAZ — "abonesi yok" ile
 * "abone sayisini bilmiyoruz" ayni nokta degildir.
 */
export function etkiEkseni(panels: readonly PanelSummary[]): EtkiEkseni {
  const known = panels.filter((p) => p.abone_sayisi != null);
  if (known.length === 0) {
    return { mode: false, max: 100, missing: 0 };
  }
  return {
    mode: true,
    max: niceMax(Math.max(...known.map((p) => p.abone_sayisi ?? 0))),
    missing: panels.length - known.length,
  };
}

/** Bakim vadesi rozeti (F-21). */
export interface BakimVadesi {
  /** true: vade GECMIS. */
  gecti: boolean;
  /** Vadeye (veya vadeden beri) kalan tam gun sayisi, her zaman >= 0. */
  gun: number;
  metin: string;
}

/**
 * Bakim vadesini rozet metnine cevirir.
 *
 * ESIK YOK — bilerek. Depo kurali esik sayilarinin arayuze GOMULMEMESIDIR (PLAN.md kural 10)
 * ve "bakima N gun kala uyar" turunden bir sinir bu depoda hicbir yerde tanimli degil.
 * Uydurmak yerine yalnizca (vade - simdi) ISARETI kullaniliyor: vade gecti mi, gecmedi mi.
 * Bu, olcmedigimiz bir esigi varmis gibi gostermeden gercek bilgiyi verir.
 *
 * Kunye ice aktarilmamissa null doner: rozet hic cizilmez (bos rozet "bakim yok" gibi okunurdu).
 */
export function bakimVadesi(sonrakiBakimAt: string | null | undefined, now = Date.now()): BakimVadesi | null {
  if (!sonrakiBakimAt) return null;
  const due = Date.parse(sonrakiBakimAt);
  if (Number.isNaN(due)) return null;
  const gun = Math.floor(Math.abs(due - now) / 86_400_000);
  const gecti = due < now;
  return { gecti, gun, metin: gecti ? `Bakım vadesi ${gun} gün geçti` : `Bakıma ${gun} gün` };
}
