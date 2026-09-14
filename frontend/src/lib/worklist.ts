import type { Alarm, PanelDetail, PanelSummary, Prio } from "../api/types";
import { ttlText } from "./format";
import { alarmText, pointLabel } from "./labels";

// Ekran penceresi, alarm esigi degil: zaman ekseni onumuzdeki 14 gunu gosterir.
export const AXIS_DAYS = 14;
export const AXIS_HOURS = AXIS_DAYS * 24;

// Operator icin aciliyet sirasi: kritik > alarm > izleme kopuklugu > uyari > bilgi.
export const URGENCY: Record<Prio, number> = { P1: 0, P2: 1, SYS: 2, P3: 3, INFO: 4 };
export const prioRank = (prio: Prio): number => URGENCY[prio];

/** Panonun is listesindeki onceligi. Haberlesmesi kopan pano, alarmi olmasa da SYS sayilir. */
export function effectivePrio(panel: PanelSummary): Prio | null {
  if (panel.top_prio && panel.top_prio !== "INFO") return panel.top_prio;
  if (!panel.comms_ok) return "SYS";
  return null;
}

export const needsAttention = (panel: PanelSummary) => effectivePrio(panel) !== null;

const ttlOrInfinity = (hours: number | null | undefined) => (hours == null ? Number.POSITIVE_INFINITY : hours);

/** Ilgi bekleyen panolar: oncelik, sonra sinira kalan sure, sonra risk skoru. */
export function sortWorklist(panels: PanelSummary[]): PanelSummary[] {
  return panels.filter(needsAttention).sort((a, b) => {
    const byPrio = URGENCY[effectivePrio(a)!] - URGENCY[effectivePrio(b)!];
    if (byPrio !== 0) return byPrio;
    const byTtl = ttlOrInfinity(a.ttl_h) - ttlOrInfinity(b.ttl_h);
    if (byTtl !== 0) return byTtl;
    if (b.risk_score !== a.risk_score) return b.risk_score - a.risk_score;
    return a.pano_id.localeCompare(b.pano_id);
  });
}

/** Logaritmik eksen: yakin gelecek genis, uzak gelecek sikisik. 0 -> 0, AXIS_HOURS -> 1. */
export function axisFraction(hours: number): number {
  const clamped = Math.min(Math.max(hours, 0), AXIS_HOURS);
  return Math.log1p(clamped) / Math.log1p(AXIS_HOURS);
}

export interface AxisGeometry {
  /** Eksen kabinin genisligi (px). */
  trackPx: number;
  /** "Simdi" kutusundan sonra eksenin basladigi yer (px). */
  startPx: number;
  /** Son kartin tasmamasi icin sagda birakilan pay (px). */
  endPadPx: number;
  /** Isaret + kart genisligi (px); kart, isaretin 14 px solundan baslar. */
  cardPx: number;
  rows: number;
}

const MARK_CENTER_PX = 14;

/**
 * Sureye gore dizili kartlari satirlara dagitir; ayni satirda kartlar ust uste binmez.
 * Her kart cakismasiz ilk satira, hic yoksa en az cakisan satira gider. Satir 0 en ustte.
 */
export function layoutAxisRows(fractions: number[], geometry: AxisGeometry): number[] {
  const usable = Math.max(0, geometry.trackPx - geometry.startPx - geometry.endPadPx);
  const placed: Array<{ left: number; right: number; row: number }> = [];
  return fractions.map((fraction) => {
    const left = geometry.startPx + usable * fraction - MARK_CENTER_PX;
    const right = left + geometry.cardPx;
    let bestRow = 0;
    let bestConflicts = Number.POSITIVE_INFINITY;
    for (let row = 0; row < geometry.rows; row++) {
      const conflicts = placed.filter((p) => p.row === row && p.left < right && left < p.right).length;
      if (conflicts < bestConflicts) {
        bestRow = row;
        bestConflicts = conflicts;
      }
      if (conflicts === 0) break;
    }
    placed.push({ left, right, row: bestRow });
    return bestRow;
  });
}

export function fleetHeadline(worklist: PanelSummary[]): string {
  if (worklist.length === 0) return "Tüm panolar normal çalışıyor.";
  const now = worklist.filter((p) => p.ttl_h == null).length;
  const upcoming = worklist.filter((p) => p.ttl_h != null && p.ttl_h <= AXIS_HOURS).length;
  const parts: string[] = [];
  if (now > 0) parts.push(`${now} pano şimdi ilgi bekliyor`);
  if (upcoming > 0) parts.push(`${upcoming} pano önümüzdeki ${AXIS_DAYS} günde sınıra ulaşıyor`);
  if (parts.length === 0) parts.push(`${worklist.length} pano izlemede`);
  return `${parts.join(", ")}.`;
}

export function panelHeadline(panel: PanelSummary): string {
  if (!panel.comms_ok) return "Merkez bağlantısı koptu";
  return panel.top_alarm ? alarmText(panel.top_alarm) : "Normal çalışıyor";
}

/** Detay ekraninin ana alarmi: en acil oncelik, onaysiz once, en yeni once. */
export function primaryAlarm(alarms: Alarm[]): Alarm | null {
  const open = alarms.filter((a) => a.state !== "cleared");
  open.sort(
    (a, b) =>
      URGENCY[a.prio] - URGENCY[b.prio] ||
      Number(a.state !== "active") - Number(b.state !== "active") ||
      Date.parse(b.raised_at) - Date.parse(a.raised_at),
  );
  return open[0] ?? null;
}

/** Detay ekraninin tek cumlelik ozeti. */
export function panelStatement(detail: PanelDetail, primary: Alarm | null): string {
  if (!primary) return detail.points.length > 0 ? "Pano normal çalışıyor." : "Bu panodan henüz veri gelmedi.";
  const point = primary.reason?.point;
  const ttl = ttlText(primary.ttl_h);
  if (point && ttl) return `${pointLabel(point)} bağlantısı, yük değişmezse yaklaşık ${ttl} sonra sıcaklık sınırını aşacak.`;
  return `${alarmText(primary.code, primary.text)}.`;
}
