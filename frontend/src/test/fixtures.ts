/**
 * Bilesen testleri icin ortak fikstürler (K7 / 7.1).
 *
 * KURAL: buradaki her alan `src/api/types.ts`teki tipten gelir; alan adi UYDURULMAZ.
 * Fikstur tipli oldugu icin sozlesme degisirse `npm run build` (tsc --noEmit) kirilir —
 * yani fikstur de sozlesmeye baglidir.
 */
import type { Alarm, FleetKpi, PanelSummary } from "../api/types";
import type { FleetState } from "../state/fleet";

/**
 * `ago()` goreli sure yazar; testin cikti metni zamana gore degismesin diye
 * sabit bir GECMIS an kullanilir. 2024-01-01 -> her kosuda "N gün önce" dalina duser
 * (format.ts:39-40), yani metin kalibi sabittir. Bu bir VARSAYIM degil, format.ts'in
 * okunan davranisidir.
 */
export const GECMIS_AN = "2024-01-01T00:00:00Z";

/**
 * DORT baslikli alarm: `reason.verify` DOLU.
 *
 * Bu alan sart: AlarmNedeni.tsx:90 `{verify && (` — `verify` yoksa ekranda dort degil
 * UC <h3> olur. Fikstur `verify` icermeseydi "dort baslik" testi yanlis seyi olcerdi.
 */
export const ALARM_TAM: Alarm = {
  id: "ALM-TEST-1",
  pano_id: "ADM-00001",
  code: "ALM-K-ALM",
  prio: "P2",
  state: "active",
  raised_at: GECMIS_AN,
  // ADVICE_TEXT anahtari SOZLESMEDEKI metnin kendisidir (labels.ts:69-71); API bunu gonderir.
  advice: "Planli bakimda tork kontrolu ve temizlik; kritik evrede yuk azaltma onerisi",
  ttl_h: 209,
  notified: ["sms"],
  reason: {
    signals: [
      { tag: "t_conn.GIRIS_L1.k_ratio", value: 1.72, threshold: 1.6 },
      { tag: "health.prot_health_ok", value: 1 },
    ],
    layer: "L1",
    basis: "K/K₀ = 1,72 (eşik 1,60)",
    point: "GIRIS_L1",
    verify: { hypothesis: "HYP-LOOSE-CONN", missing: ["ALM-DQ-DRIFT"], total: 3 },
  },
};

/**
 * `reason` alani HIC YOK — backend'in eski bir surumu ya da karantinadan gecmis bir
 * kayit boyle gelebilir. `Alarm.reason` tipte zaten `?: AlarmReason | null`.
 */
export const ALARM_REASONSIZ: Alarm = {
  id: "ALM-TEST-2",
  pano_id: "ADM-00002",
  code: "ALM-COMMS-LOST",
  prio: "P3",
  state: "active",
  raised_at: GECMIS_AN,
};

export const PANO: PanelSummary = {
  pano_id: "ADM-00001",
  name: "Aydın OSB Fider 3",
  risk_score: 72,
  risk_mode: "HYP-LOOSE-CONN",
  top_alarm: "ALM-K-ALM",
  top_prio: "P2",
  ttl_h: 209,
  last_seen: GECMIS_AN,
  comms_ok: true,
};

export const KPI: FleetKpi = { p95_end_to_end_ms: 412 };

/**
 * FleetState'in YEDI alani da verilir (state/fleet.tsx:11-20). Eksik alan birakmak
 * yerine varsayilanlari burada toplamak, yeni bir alan eklendiginde tsc'nin TEK yerde
 * kirilmasini saglar.
 */
export function fleetState(over: Partial<FleetState> = {}): FleetState {
  return {
    panels: [],
    loaded: true,
    error: null,
    kpi: null,
    stream: "open",
    lastSync: Date.parse(GECMIS_AN),
    touched: {},
    ...over,
  };
}
