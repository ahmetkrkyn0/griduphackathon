// EK-II/14 olculerine (1600 x 1500 x 450 mm) gore KENDI cizimimizin geometrisi.
// Komitenin PDF'inden gorsel alinmaz. 2D on gorunus ve (TC2) 3D ikiz ayni koordinatlari kullanir.
// Birim mm; 2D'de y yukaridan asagi artar.

import type { ConnPoint } from "../api/types";

export const PANEL_MM = { width: 1600, height: 1500, depth: 450 } as const;
export const ZONE_Y = { topCompartmentEnd: 350, cableZoneStart: 1100 } as const; // kablo bolgesi >= 400 mm
export const BAR_Y = { L1: 510, L2: 695, L3: 880 } as const;
export const N_BAR_Y = 1290;
export const DSYA_COUNT = 7; // Tablo 8: 5 cikis + 2 yedek
export const FIRST_SPARE_DSYA = 6;
export const TERMINAL_Y = 1080;

export const dsyaX = (n: number) => 120 + 160 * (n - 1);
export const girisX = (phase: 1 | 2 | 3) => 1330 + 70 * (phase - 1);
export const GIRIS_N_X = 1540;

export function pointPos(pt: string): { x: number; y: number } | null {
  const dsya = /^DSYA(\d)_L([123])$/.exec(pt);
  if (dsya) return { x: dsyaX(Number(dsya[1])) + (Number(dsya[2]) - 2) * 30, y: TERMINAL_Y };
  if (pt === "GIRIS_N") return { x: GIRIS_N_X, y: N_BAR_Y };
  const giris = /^GIRIS_L([123])$/.exec(pt);
  if (giris) {
    const phase = Number(giris[1]) as 1 | 2 | 3;
    return { x: girisX(phase), y: BAR_Y[`L${phase}`] };
  }
  return null;
}

// 3D ikiz: 2D ile ayni x; y yukari artar (three.js), z arka duvardan on yuze (0..450).
export const LUG_Z = 280; // DSYA kablo pabuclari
export const BAR_TAP_Z = 200; // giris baralari

export function pointPos3d(pt: string): { x: number; y: number; z: number } | null {
  const pos = pointPos(pt);
  if (!pos) return null;
  return { x: pos.x, y: PANEL_MM.height - pos.y, z: pt.startsWith("DSYA") ? LUG_Z : BAR_TAP_Z };
}

const PHASE_ORDER = ["L1", "L2", "L3", "N"];

/** Ayni cikisin (DSYA-n) veya girisin tum fazlari, L1-L2-L3-N sirasiyla. */
export function phaseGroup(points: ConnPoint[], pt: string): ConnPoint[] {
  const match = /^(DSYA\d|GIRIS)_/.exec(pt);
  if (!match) return [];
  const prefix = match[0];
  return points
    .filter((p) => p.pt.startsWith(prefix))
    .sort((a, b) => PHASE_ORDER.indexOf(a.pt.slice(prefix.length)) - PHASE_ORDER.indexOf(b.pt.slice(prefix.length)));
}
