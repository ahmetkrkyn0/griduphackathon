// ORNEK VERI — yalnizca `npm run dev:mock` (VITE_USE_MOCKS=1) ile kullanilir.
// Yanitlar backend/app/api/views.py'nin urettigi bicimdedir (openapi.yaml).
// Buradaki esik degerleri API'nin gonderecegi yanit ornegidir; arayuz mantigi bunlari kullanmaz.

import { pointLabel } from "../lib/labels";
import { ApiError } from "./errors";
import { ARC_EVENT, PROT_HEALTH, bucketStarts, seriesPoint, stepToMs } from "./mockSeries";
import type {
  Alarm,
  AlarmReason,
  Api,
  Blackbox,
  ConnPoint,
  Elec,
  Env,
  FleetKpi,
  PanelDetail,
  PanelHealth,
  PanelSummary,
  Prio,
  SeriesResponse,
  ShelveBody,
  StreamMessage,
  TimelineEntry,
  Tvoc,
} from "./types";

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
  arc: "Kritik alarm; olay oncesi 72 saatlik kara kutu raporu. Reset SAHADA yapilir.",
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
  { pano_id: PROT_HEALTH.panoId, name: "Bornova DM-3", mode: "HYP-PROT-LOSS", prio: "P1", code: "ALM-PROT-HEALTH", risk: 88, ttl_h: null, comms_ok: true, baseline_day: 64 },
  { pano_id: "ADM-00014", name: "Efeler TM-14", mode: "HYP-LOOSE-CONN", prio: "P2", code: "ALM-K-ALM", risk: 72, ttl_h: 146, comms_ok: true, baseline_day: 42 },
  { pano_id: "ADM-00102", name: "Merkezefendi TM-7", mode: "HYP-CONDENSE", prio: "P2", code: "ALM-DEW-ALM", risk: 55, ttl_h: null, comms_ok: true, baseline_day: 88 },
  { pano_id: "GDZ-00088", name: "Yunusemre TM-21", mode: "HYP-OVERLOAD", prio: "P2", code: "ALM-I-OVER", risk: 38, ttl_h: null, comms_ok: true, baseline_day: 51 },
  { pano_id: "GDZ-00410", name: "Karşıyaka TM-9", mode: "HYP-SELF-FAULT", prio: null, code: null, risk: 20, ttl_h: null, comms_ok: false, baseline_day: 33 },
  { pano_id: "ADM-00076", name: "Söke TM-4", mode: "HYP-LOOSE-CONN", prio: "P3", code: "ALM-K-WARN", risk: 27, ttl_h: 61, comms_ok: true, baseline_day: 19 },
  { pano_id: "ADM-00057", name: "Bodrum TM-2", mode: "HYP-LOOSE-CONN", prio: "P3", code: "ALM-TTL-14D", risk: 31, ttl_h: 290, comms_ok: true, baseline_day: 120 },
  // Kara kutu (Olay Analizi) senaryosunun kahramani: TVOC-2 ark tripi + oncesindeki isinma.
  { pano_id: ARC_EVENT.panoId, name: "Selçuk TM-1", mode: "HYP-ARC", prio: "P1", code: "ALM-ARC-TRIP", risk: 95, ttl_h: null, comms_ok: true, baseline_day: 77 },
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
    case PROT_HEALTH.panoId:
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
    case ARC_EVENT.panoId:
      tvoc = { ...tvoc, trips: 1, prot_health_ok: true, last_trip_at: isoAgo(ARC_EVENT.occurredAgoMs), last_det_label: "X1:7" };
      alarms.push(alarm("60", seed, "ALM-ARC-TRIP", "P1", ARC_EVENT.occurredAgoMs / 60_000,
        { signals: [{ tag: "tvoc.trips", value: 1, threshold: 0, unit: "" }], layer: "L0", point: null, basis: "TVOC-2 PDU 149 trip sayaci degisimi" },
        ADVICE.arc, { notified: ["sms", "whatsapp", "call"], escalation_level: 2 }));
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

// Panonun adindaki ilk kelime gercek bir ilce/semt adi (Efeler, Bornova, Soke...) — ADM/GDZ'nin
// gercek hizmet bolgesindeki (Aydin/Denizli/Mugla + Izmir/Manisa) ilce merkezlerinin yaklasik
// enlem/boylami. Sozlesmede PanelSummary.lat/lon zaten onayli bir alan (contracts/openapi.yaml);
// bu yalnizca demo/mock verisine gercek koordinat doldurmak — dogrusal olcek/GK4 uyumlu bir
// "gercek konum" gorunumu (bkz. BolgeHaritasi.tsx) icin. Ilce MERKEZI hassasiyetinde (birkac km),
// gercek trafo/pano GPS pini degil — bu, kod ici yorumla ve ekrandaki metinle acikca belirtilir.
const DISTRICT_COORDS: Record<string, [number, number]> = {
  Efeler: [37.856, 27.8416],
  Nazilli: [37.9145, 28.32],
  Söke: [37.7328, 27.4058],
  Didim: [37.4165, 27.2633],
  Kuşadası: [37.8579, 27.261],
  Merkezefendi: [37.7765, 29.0864],
  Pamukkale: [37.92, 29.125],
  Tavas: [37.5667, 29.0833],
  Bodrum: [37.0343, 27.4305],
  Menteşe: [37.2153, 28.3636],
  Fethiye: [36.6217, 29.1164],
  Bornova: [38.467, 27.22],
  Karşıyaka: [38.461, 27.1189],
  Selçuk: [37.95, 27.3667],
  Buca: [38.3667, 27.1667],
  Çiğli: [38.495, 27.07],
  Yunusemre: [38.617, 27.44],
  Turgutlu: [38.5, 27.7],
  Alaşehir: [38.35, 28.5167],
  Salihli: [38.4833, 28.1333],
};

function districtCoords(name: string): [number, number] | null {
  return DISTRICT_COORDS[name.split(" ")[0]] ?? null;
}

function summary(seed: Seed): PanelSummary {
  const detail = details.get(seed.pano_id);
  const coords = districtCoords(seed.name);
  return {
    pano_id: seed.pano_id, name: seed.name, lat: coords?.[0] ?? null, lon: coords?.[1] ?? null, pano_type: PANO_TYPE,
    risk_score: seed.risk, risk_mode: seed.mode, top_alarm: seed.code, top_prio: seed.prio, ttl_h: seed.ttl_h,
    last_seen: detail?.ts ?? isoAgo(5000), comms_ok: seed.comms_ok, baseline_day: seed.baseline_day,
  };
}

function allAlarms(): Alarm[] {
  return [...details.values()].flatMap((d) => d.active_alarms ?? []);
}

function findAlarm(alarmId: string): Alarm | undefined {
  return allAlarms().find((a) => a.id === alarmId);
}

// GET /events/{id}/blackbox icin sabit olay kaydi. Olay bulunduktan sonra zaman cizelgesi
// donmuyor (mock module yuklendiginde bir kez hesaplanir) — canli demo suresince gecerlidir.
const BLACKBOX_PANEL_TAGS = [
  "elec.i_ph.0", "elec.i_ph.1", "elec.i_ph.2", "elec.i_n",
  "env.t_low_c", "env.rh_low_pct", "env.td_margin_k",
  "tvoc.trips", "tvoc.prot_health_ok", "risk.score",
];
const BLACKBOX_STEPS_MIN = [1, 5, 10, 15, 30, 60];

interface MockEvent {
  event_id: string;
  pano_id: string;
  occurred_at: string;
  code: string;
  point: string | null;
  det_label: string | null;
  timeline: TimelineEntry[];
}

const EVENTS: Record<string, MockEvent> = {
  "EVT-60": {
    event_id: "EVT-60", pano_id: ARC_EVENT.panoId, occurred_at: isoAgo(ARC_EVENT.occurredAgoMs),
    code: "ALM-ARC-TRIP", point: null, det_label: "X1:7",
    timeline: [
      { ts: isoAgo(ARC_EVENT.precursorAgoMs), kind: "alarm", text: "ALM-K-WARN (P3, Giriş L1) oluştu: Isıl direnç indeksi K/K₀ > 1,3 — bağlantı direnci artışı şüphesi" },
      { ts: isoAgo(ARC_EVENT.occurredAgoMs), kind: "trip", text: "ALM-ARC-TRIP (P1) oluştu: TVOC-2 ark tripi" },
      { ts: isoAgo(ARC_EVENT.occurredAgoMs - minutes(1)), kind: "action", text: "ALM-ARC-TRIP (P1) bildirim iletildi: sms, whatsapp" },
      { ts: isoAgo(ARC_EVENT.occurredAgoMs - minutes(5)), kind: "action", text: "ALM-ARC-TRIP (P1) arama" },
      { ts: isoAgo(ARC_EVENT.occurredAgoMs - minutes(15)), kind: "action", text: "ALM-ARC-TRIP (P1) üst amire eskalasyon" },
    ],
  },
  "EVT-42": {
    event_id: "EVT-42", pano_id: "ADM-00014", occurred_at: isoAgo(minutes(41)),
    code: "ALM-K-ALM", point: "DSYA3_L2", det_label: null,
    timeline: [
      { ts: isoAgo(minutes(41)), kind: "alarm", text: "ALM-K-ALM (P2, DSYA-3 L2) oluştu: Isıl direnç indeksi K/K₀ > 1,6 — gevşek/oksitlenmiş bağlantı" },
      { ts: isoAgo(minutes(40)), kind: "action", text: "ALM-K-ALM (P2, DSYA-3 L2) bildirim iletildi: sms, whatsapp" },
    ],
  },
  // Y2 (olay modu) P1 kartindaki "Kara kutuyu ac" kisayolu her P1 alarm icin calissin diye eklendi;
  // eskiden yalnizca EVT-60/EVT-42 vardi, ALM-PROT-HEALTH (id "51") 404 veriyordu.
  "EVT-51": {
    event_id: "EVT-51", pano_id: PROT_HEALTH.panoId, occurred_at: isoAgo(minutes(3)),
    code: "ALM-PROT-HEALTH", point: null, det_label: "X2:4",
    timeline: [
      { ts: isoAgo(minutes(4)), kind: "note", text: "TVOC-2 PDU 222/223 sensör durumu hata bitini işaretledi (dedektör X2:4)" },
      { ts: isoAgo(minutes(3)), kind: "alarm", text: "ALM-PROT-HEALTH (P1) oluştu: Ark koruması sağlık durumu arızalı — pano sessizce korumasız" },
      { ts: isoAgo(minutes(2)), kind: "action", text: "ALM-PROT-HEALTH (P1) bildirim iletildi: sms, whatsapp" },
    ],
  },
};

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
  async fleetHealth(): Promise<PanelHealth[]> {
    await delay(150);
    // Gercek uc gibi davranir: veri gondermemis panoda saglik alanlari null doner,
    // 0 yazilmaz (0 dBm gecerli bir RSSI'dir).
    return SEEDS.map((seed) => {
      const health = details.get(seed.pano_id)?.health;
      const s = summary(seed);
      return {
        pano_id: seed.pano_id,
        name: seed.name,
        nodes_ok: health?.nodes_ok ?? null,
        nodes_total: health?.nodes_total ?? null,
        rssi_dbm: health?.rssi_dbm ?? null,
        vbak_pct: health?.vbak_pct ?? null,
        buffered: health?.buffered ?? null,
        maint_mode: health?.maint_mode ?? null,
        fw: health?.fw ?? null,
        baseline_day: health?.baseline_day ?? seed.baseline_day,
        last_seen: s.last_seen,
        comms_ok: seed.comms_ok,
      };
    });
  },
  async fleetKpi(): Promise<FleetKpi> {
    const ok = SEEDS.filter((s) => s.comms_ok).length;
    const active: Record<string, number> = { P1: 0, P2: 0, P3: 0, INFO: 0, SYS: 0 };
    for (const a of allAlarms()) if (a.state === "active" || a.state === "acked") active[a.prio] = (active[a.prio] ?? 0) + 1;
    return {
      panels_total: SEEDS.length,
      comms_ok_pct: +((100 * ok) / SEEDS.length).toFixed(1),
      alarms_per_100_panels_per_day: 3.1,
      active_by_prio: active,
      distribution_pct: { P1: 5.1, P2: 14.8, P3: 80.1 },
      p95_end_to_end_ms: 606,
      ingest_msgs_per_s: SEEDS.length / 10,
    };
  },
  async ack(alarmId, body) {
    await delay(200);
    const target = findAlarm(alarmId);
    if (!target) throw new ApiError(404, `alarm bulunamadi: ${alarmId}`);
    if (target.state !== "active") throw new ApiError(409, "alarm zaten onayli veya temizlenmis");
    Object.assign(target, { state: "acked", acked_at: new Date().toISOString(), acked_by: body.by });
    return { ok: true };
  },
  async shelve(alarmId, body: ShelveBody) {
    await delay(200);
    const target = findAlarm(alarmId);
    if (!target) throw new ApiError(404, `alarm bulunamadi: ${alarmId}`);
    if (target.prio === "P1") throw new ApiError(403, "P1 alarm rafa alinamaz (suppressible=false)");
    if (target.state !== "active" && target.state !== "acked") throw new ApiError(409, "alarm zaten temizlenmis");
    Object.assign(target, {
      state: "shelved",
      shelved_until: new Date(Date.now() + body.minutes * 60_000).toISOString(),
    });
    return { ok: true };
  },
  async alarms(query) {
    await delay(150);
    const states = new Set((query?.state ?? "active,acked").split(","));
    const prios = query?.prio ? new Set(query.prio.split(",")) : null;
    let list = allAlarms().filter((a) => states.has(a.state) && (!prios || prios.has(a.prio)) && (!query?.pano_id || a.pano_id === query.pano_id));
    list = list.sort((a, b) => Date.parse(b.raised_at) - Date.parse(a.raised_at));
    return list.slice(0, query?.limit ?? 100);
  },
  async series(panoId, tags, from, to, step = "1m") {
    await delay(180);
    if (!details.has(panoId)) throw new ApiError(404, `pano bulunamadi: ${panoId}`);
    const stepMs = stepToMs(step);
    const buckets = bucketStarts(from.getTime(), to.getTime(), stepMs);
    if (buckets.length > 4000) throw new ApiError(422, "cok fazla nokta istendi: araligi daraltin veya step'i buyutun");
    const out: SeriesResponse = {};
    for (const tag of tags) out[tag] = buckets.map((t) => [t, seriesPoint(panoId, tag, t)]);
    return out;
  },
  async blackbox(eventId, windowH = 72): Promise<Blackbox> {
    await delay(200);
    const event = EVENTS[eventId];
    if (!event) throw new ApiError(404, `olay bulunamadi: ${eventId}`);
    const occurred = Date.parse(event.occurred_at);
    const start = occurred - windowH * 3_600_000;
    const end = occurred + 3_600_000; // BLACKBOX_TAIL: olay sonrasi 1 saat
    const stepMs = (BLACKBOX_STEPS_MIN.find((m) => Math.ceil((end - start) / (m * 60_000)) <= 500) ?? 60) * 60_000;
    const buckets = bucketStarts(start, end, stepMs);
    const tags = event.point ? [`t_conn.${event.point}.t_c`, `t_conn.${event.point}.dt_c`, `t_conn.${event.point}.k_ratio`, ...BLACKBOX_PANEL_TAGS] : BLACKBOX_PANEL_TAGS;
    const series: SeriesResponse = {};
    for (const tag of tags) series[tag] = buckets.map((t) => [t, seriesPoint(event.pano_id, tag, t)]);
    return {
      event_id: event.event_id, pano_id: event.pano_id, occurred_at: event.occurred_at,
      code: event.code, det_label: event.det_label, window_h: windowH, series, timeline: event.timeline,
    };
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
