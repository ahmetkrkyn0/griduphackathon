// ORNEK VERI — yalnizca `npm run dev:mock` (VITE_USE_MOCKS=1) ile kullanilir.
// Yanitlar backend/app/api/views.py'nin urettigi bicimdedir (openapi.yaml).
// Buradaki esik degerleri API'nin gonderecegi yanit ornegidir; arayuz mantigi bunlari kullanmaz.

import { pointLabel } from "../lib/labels";
import { ApiError } from "./errors";
import type { Alarm, AlarmReason, Api, ConnPoint, Elec, Env, FleetKpi, PanelDetail, PanelSummary, Prio, StreamMessage, Tvoc } from "./types";

const LOADED_AT = Date.now();
const AMBIENT_C = 24.1;
const PANO_TYPE = "1600kVA-dahili";

const isoAgo = (ms: number) => new Date(Date.now() - ms).toISOString();
const minutes = (m: number) => m * 60_000;
const delay = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

// Sozlesmedeki hypotheses[].advice metinleri (API bunlari ASCII olarak gonderir)
const ADVICE = {
  loose: "Planli bakimda tork kontrolu ve temizlik; kritik evrede yuk azaltma onerisi",
  overload: "Yuk transferi / fider duzenleme onerisi",
  condense: "Anti-kondensasyon isiticisi ac; conta ve havalandirma kontrolu",
  prot: "Dedektor/fiber bakimi — pano korumasiz",
  self: "Uzaktan diagnostik; gerekirse saha ziyareti. ARIZA ALARMI DEGIL.",
};

interface Seed {
  pano_id: string;
  name: string;
  mode: string;
  prio: Prio | null;
  code: string | null;
  risk: number;
  ttl_h: number | null;
  comms_ok: boolean;
  baseline_day: number;
}

const SEEDS: Seed[] = [
  { pano_id: "GDZ-00231", name: "Bornova DM-3", mode: "HYP-PROT-LOSS", prio: "P1", code: "ALM-PROT-HEALTH", risk: 88, ttl_h: null, comms_ok: true, baseline_day: 64 },
  { pano_id: "ADM-00014", name: "Efeler TM-14", mode: "HYP-LOOSE-CONN", prio: "P2", code: "ALM-K-ALM", risk: 72, ttl_h: 146, comms_ok: true, baseline_day: 42 },
  { pano_id: "ADM-00102", name: "Merkezefendi TM-7", mode: "HYP-CONDENSE", prio: "P2", code: "ALM-DEW-ALM", risk: 55, ttl_h: null, comms_ok: true, baseline_day: 88 },
  { pano_id: "GDZ-00088", name: "Yunusemre TM-21", mode: "HYP-OVERLOAD", prio: "P2", code: "ALM-I-OVER", risk: 38, ttl_h: null, comms_ok: true, baseline_day: 51 },
  { pano_id: "GDZ-00410", name: "Karşıyaka TM-9", mode: "HYP-SELF-FAULT", prio: null, code: null, risk: 20, ttl_h: null, comms_ok: false, baseline_day: 33 },
  { pano_id: "ADM-00076", name: "Söke TM-4", mode: "HYP-LOOSE-CONN", prio: "P3", code: "ALM-K-WARN", risk: 27, ttl_h: 61, comms_ok: true, baseline_day: 19 },
  { pano_id: "ADM-00057", name: "Bodrum TM-2", mode: "HYP-LOOSE-CONN", prio: "P3", code: "ALM-TTL-14D", risk: 31, ttl_h: 290, comms_ok: true, baseline_day: 120 },
];

const NORMAL_NAMES = [
  "Nazilli TM-5", "Turgutlu DM-1", "Didim TM-8", "Pamukkale TM-3", "Menteşe TM-6", "Alaşehir TM-2",
  "Buca TM-11", "Kuşadası TM-5", "Fethiye TM-9", "Çiğli DM-4", "Salihli TM-7", "Tavas TM-1",
];
NORMAL_NAMES.forEach((name, i) => {
  SEEDS.push({
    pano_id: `${i % 2 ? "GDZ" : "ADM"}-${String(301 + i).padStart(5, "0")}`,
    name,
    mode: "HYP-NORMAL",
    prio: null,
    code: null,
    risk: 2 + ((i * 7) % 9),
    ttl_h: null,
    comms_ok: true,
    baseline_day: 20 + i * 3,
  });
});

function point(pt: string, dt: number, kRatio: number | null): ConnPoint {
  return {
    pt, label: pointLabel(pt), t_c: +(AMBIENT_C + dt).toFixed(1), dt_c: dt,
    k: null, k_ratio: kRatio, tau_s: kRatio == null ? null : 900, ttl_h: null,
    excited: kRatio != null, q: 0, state: "normal",
  };
}

function basePoints(): ConnPoint[] {
  const points: ConnPoint[] = [];
  const giris: Array<[string, number]> = [["L1", 28.4], ["L2", 29.1], ["L3", 27.6], ["N", 9.8]];
  for (const [phase, dt] of giris) points.push(point(`GIRIS_${phase}`, dt, phase === "N" ? null : 1.02));
  const dsya = [19.2, 22.8, 21.4, 17.6, 15.9, 1.8, 1.6]; // DSYA-6/7 yedek, yuksuz
  dsya.forEach((dt, i) => {
    ["L1", "L2", "L3"].forEach((phase, j) => {
      const spare = i >= 5;
      points.push(point(`DSYA${i + 1}_${phase}`, +(dt + [0.4, -0.3, 0.1][j]).toFixed(1), spare ? null : +(1 + j * 0.02).toFixed(2)));
    });
  });
  return points;
}

function patch(points: ConnPoint[], pt: string, change: Partial<ConnPoint>) {
  const target = points.find((p) => p.pt === pt);
  if (!target) return;
  Object.assign(target, change);
  if (change.dt_c != null) target.t_c = +(AMBIENT_C + change.dt_c).toFixed(1);
}

function alarm(id: string, seed: Seed, code: string, prio: Prio, minsAgo: number, reason: AlarmReason, advice: string, extra: Partial<Alarm> = {}): Alarm {
  return {
    id, event_id: `EVT-${id}`, pano_id: seed.pano_id, code, text: code, prio, state: "active",
    raised_at: isoAgo(minutes(minsAgo)), cleared_at: null, acked_at: null, acked_by: null, shelved_until: null,
    escalation_level: 0, notified: prio === "P1" || prio === "P2" ? ["sms", "whatsapp"] : [],
    reason, advice, ttl_h: null, ...extra,
  };
}

function buildDetail(seed: Seed): PanelDetail {
  const points = basePoints();
  let env: Env = { t_low_c: 24.1, rh_low_pct: 61, td_low_c: 16.1, td_margin_k: 7.9, t_up_c: 31.8, rh_up_pct: 44, dt_air_k: 7.7, voc_idx: null, door_open: false };
  let elec: Elec = { i_ph: [612, 655, 598], i_n: 48, u_ph: [229.8, 231.2, 230.4], thd_i: [6.1, 6.8, 5.9], cosphi: 0.96, unbal_pct: 4.6 };
  let tvoc: Tvoc = { state: 1, trips: 0, prot_health_ok: true, comm_ok: true, last_trip_at: null, last_det_label: null };
  const alarms: Alarm[] = [];
  let ts = isoAgo(8000);

  switch (seed.pano_id) {
    case "ADM-00014":
      patch(points, "DSYA3_L2", { dt_c: 34.3, k_ratio: 1.64, ttl_h: 146, state: "alarm" });
      alarms.push(alarm("42", seed, "ALM-K-ALM", "P2", 41,
        { signals: [{ tag: "t_conn.DSYA3_L2.k_ratio", value: 1.64, threshold: 1.6, unit: "K/K0" }], layer: "L1", point: "DSYA3_L2", basis: "Rapor 6.5 L1-1" },
        ADVICE.loose, { ttl_h: 146 }));
      break;
    case "GDZ-00231":
      tvoc = { ...tvoc, state: 2, prot_health_ok: false, last_det_label: "X2:4" };
      alarms.push(alarm("51", seed, "ALM-PROT-HEALTH", "P1", 3,
        { signals: [{ tag: "tvoc.prot_health_ok", value: 0, threshold: 1, unit: "" }], layer: "L0", point: null, basis: "TVOC-2 PDU 222/223 sensor status, PDU 1300 hata biti" },
        ADVICE.prot));
      break;
    case "ADM-00102":
      env = { ...env, t_low_c: 14.6, rh_low_pct: 96, td_low_c: 13.9, td_margin_k: 0.8 };
      alarms.push(alarm("47", seed, "ALM-DEW-ALM", "P2", 18,
        { signals: [{ tag: "env.td_margin_k", value: 0.8, threshold: 1.0, unit: "K" }], layer: "L1", point: null, basis: "Magnus formulu" },
        ADVICE.condense, { state: "acked", acked_at: isoAgo(minutes(12)), acked_by: "ayse.k", notified: ["sms", "whatsapp", "relay"] }));
      break;
    case "GDZ-00088":
      for (const p of points) if (p.pt.startsWith("DSYA") && p.k_ratio != null) patch(points, p.pt, { dt_c: +(p.dt_c + 12).toFixed(1) });
      elec = { ...elec, i_ph: [2410, 2388, 2402], i_n: 62, thd_i: [7.2, 7.5, 7.1] };
      alarms.push(alarm("39", seed, "ALM-I-OVER", "P2", 66,
        { signals: [{ tag: "elec.i_ph.0", value: 2410, threshold: 2312, unit: "A" }], layer: "L0", point: null, basis: "EK-I/8 Tablo 8 (DSYA 250/400 A, giris 2312 A)" },
        ADVICE.overload, { state: "acked", acked_at: isoAgo(minutes(58)), acked_by: "mehmet.t" }));
      break;
    case "GDZ-00410":
      for (const p of points) p.state = "stale";
      ts = new Date(LOADED_AT - minutes(7)).toISOString();
      alarms.push(alarm("55", seed, "ALM-COMMS-LOST", "SYS", 2,
        { signals: [{ tag: "last_rx_age_min", value: 7, threshold: 5, unit: "min" }], layer: "L-1", point: null },
        ADVICE.self, { notified: [] }));
      break;
    case "ADM-00076":
      patch(points, "DSYA2_L1", { dt_c: 27.5, k_ratio: 1.34, ttl_h: 61, state: "warn" });
      alarms.push(alarm("44", seed, "ALM-K-WARN", "P3", 95,
        { signals: [{ tag: "t_conn.DSYA2_L1.k_ratio", value: 1.34, threshold: 1.3, unit: "K/K0" }], layer: "L1", point: "DSYA2_L1", basis: "Rapor 6.5 L1-1" },
        ADVICE.loose, { ttl_h: 61 }));
      break;
    case "ADM-00057":
      patch(points, "GIRIS_N", { dt_c: 21.8, k_ratio: 1.38, ttl_h: 290, state: "warn" });
      alarms.push(alarm("31", seed, "ALM-TTL-14D", "P3", 320,
        { signals: [{ tag: "t_conn.GIRIS_N.ttl_h", value: 290, threshold: 336, unit: "h" }], layer: "L1", point: "GIRIS_N", basis: "Rapor 6.5 L1-2 / 15.1 sinira kalan sure" },
        ADVICE.loose, { ttl_h: 290 }));
      break;
  }

  return {
    pano_id: seed.pano_id, name: seed.name, pano_type: PANO_TYPE, ts,
    risk_score: seed.risk, risk_mode: seed.mode,
    risk_contributions: seed.code ? { [seed.code]: 1 } : {},
    points, env, elec, tvoc, pd: null,
    health: { uptime_s: 86_400 * seed.baseline_day, nodes_ok: 25, nodes_total: 25, rssi_dbm: -71, vbak_pct: 100, buffered: 0, maint_mode: false, fw: "0.3.1", baseline_day: seed.baseline_day },
    active_alarms: alarms,
  };
}

const details = new Map(SEEDS.map((seed) => [seed.pano_id, buildDetail(seed)]));

function summary(seed: Seed): PanelSummary {
  const detail = details.get(seed.pano_id);
  return {
    pano_id: seed.pano_id, name: seed.name, lat: null, lon: null, pano_type: PANO_TYPE,
    risk_score: seed.risk, risk_mode: seed.mode, top_alarm: seed.code, top_prio: seed.prio, ttl_h: seed.ttl_h,
    last_seen: detail?.ts ?? isoAgo(5000), comms_ok: seed.comms_ok, baseline_day: seed.baseline_day,
  };
}

export const mockApi: Api = {
  async panels() {
    await delay(150);
    return SEEDS.map(summary);
  },
  async panel(panoId) {
    await delay(120);
    const detail = details.get(panoId);
    if (!detail) throw new ApiError(404, `pano bulunamadi: ${panoId}`);
    return structuredClone(detail);
  },
  async fleetKpi(): Promise<FleetKpi> {
    const ok = SEEDS.filter((s) => s.comms_ok).length;
    return {
      panels_total: SEEDS.length,
      comms_ok_pct: +((100 * ok) / SEEDS.length).toFixed(1),
      alarms_per_100_panels_per_day: 3.1,
      p95_end_to_end_ms: 606,
      ingest_msgs_per_s: SEEDS.length / 10,
    };
  },
  async ack(alarmId, body) {
    await delay(200);
    for (const detail of details.values()) {
      const target = detail.active_alarms?.find((a) => a.id === alarmId);
      if (!target) continue;
      if (target.state !== "active") throw new ApiError(409, "alarm zaten onayli veya temizlenmis");
      Object.assign(target, { state: "acked", acked_at: new Date().toISOString(), acked_by: body.by });
      return { ok: true };
    }
    throw new ApiError(404, `alarm bulunamadi: ${alarmId}`);
  },
};

/** 3 sn'de bir rastgele bir panonun olcumlerini oynatir ve `tel` mesaji yayinlar. */
export function startMockStream(emit: (message: StreamMessage) => void): () => void {
  emit({ type: "hello", payload: { server_time: new Date().toISOString(), api_version: "1.0.0-ornek" } });
  const timer = setInterval(() => {
    const live = SEEDS.filter((s) => s.comms_ok);
    const seed = live[Math.floor(Math.random() * live.length)];
    const detail = details.get(seed.pano_id);
    if (!detail) return;
    for (const p of detail.points) {
      if (p.state === "stale") continue;
      p.dt_c = Math.max(0.5, +(p.dt_c + (Math.random() - 0.5) * 0.4).toFixed(1));
      p.t_c = +(AMBIENT_C + p.dt_c).toFixed(1);
    }
    detail.ts = new Date().toISOString();
    emit({ type: "tel", payload: summary(seed) });
  }, 3000);
  return () => clearInterval(timer);
}
