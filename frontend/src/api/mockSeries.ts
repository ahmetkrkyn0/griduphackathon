// ORNEK VERI — deterministik sentetik zaman serisi ureteci (yalnizca npm run dev:mock).
// Ayni (pano, etiket, zaman damgasi) girdisi HER ZAMAN ayni degeri dondurur; bu, gercek
// backend'in `GET /panels/{id}/series`'inin davranisiyla ayni ruhtadir (rapor 15.2: "seed'li,
// tekrarlanabilir"). Gercek uygulamada bu dosyanin karsiligi yok — backend TimescaleDB'den okur.

const HOUR_MS = 3_600_000;
const DAY_MS = 24 * HOUR_MS;
const AMBIENT_C = 24.1;

function fnv1a(text: string): number {
  let h = 0x811c9dc5;
  for (let i = 0; i < text.length; i++) {
    h ^= text.charCodeAt(i);
    h = Math.imul(h, 0x01000193);
  }
  return h >>> 0;
}

/** [0,1) araliginda, girdiye gore sabit sozde-rastgele deger. */
const noise = (key: string): number => fnv1a(key) / 4294967296;
const signedNoise = (key: string): number => noise(key) * 2 - 1;

function rampAt(t: number, startMs: number, endMs: number, from: number, to: number): number {
  if (t <= startMs) return from;
  if (t >= endMs) return to;
  return from + (to - from) * ((t - startMs) / (endMs - startMs));
}

/** Aksam pikli basit gunluk yuk profili, 0..1. */
function dailyLoad(t: number): number {
  const phase = (((t % DAY_MS) + DAY_MS) % DAY_MS) / DAY_MS;
  const base = 0.55 + 0.22 * Math.sin(2 * Math.PI * (phase - 0.3));
  const evening = 0.2 * Math.exp(-(((phase - 0.78) / 0.08) ** 2));
  return Math.max(0.15, Math.min(1, base + evening));
}

/** Gece nemli/gunduz kuru basit gunluk dongu, 0..1 (1 = en nemli, gece). */
function dailyHumidity(t: number): number {
  const phase = (((t % DAY_MS) + DAY_MS) % DAY_MS) / DAY_MS;
  return 0.5 + 0.4 * Math.cos(2 * Math.PI * (phase - 0.22));
}

// Sahne alan senaryolar — rapor 15.2 etiketli enjeksiyonlarinin bu ekranlardaki karsiligi.
// PanoDetay/FiloListesi'ndeki (mock.ts) sabit "su anki deger"lerle ayni hikayeyi anlatir.
export const LOOSE_CONN = { panoId: "ADM-00014", point: "DSYA3_L2", days: 14, kFrom: 1.0, kTo: 1.64, dtFrom: 19.2, dtTo: 34.3 };
export const ARC_EVENT = { panoId: "GDZ-00512", occurredAgoMs: 25 * 60_000, precursorAgoMs: 70 * 60_000 };
export const PROT_HEALTH = { panoId: "GDZ-00231", stepAgoMs: 3 * 60_000 };
export const CONDENSE = { panoId: "ADM-00102", days: 1 };

const PHASE_LETTER_INDEX: Record<string, number> = { L1: 0, L2: 1, L3: 2 };

function phaseLetterOf(pt: string): string | null {
  return /_(L[123])$/.exec(pt)?.[1] ?? null;
}

/** elecValue ile BIREBIR ayni deger: I2-dT sacilim grafiginin ayni zaman damgasinda
 * karsilastirdigi iki seri (baglanti dT'si ve faz akimi) boylece gercekten tutarlidir. */
function phaseCurrentA(panoId: string, phaseIdx: number, t: number): number {
  const seedAmp = 350 + 500 * noise(`amp|${panoId}`);
  const phaseShift = phaseIdx * 0.02;
  const overload = panoId === "GDZ-00088"; // ayni senaryo mock.ts'teki asiri yuk panosu
  const load = dailyLoad(t + phaseShift * DAY_MS) * (overload ? 3.9 : 1);
  return seedAmp * load + signedNoise(`iph|${panoId}|${phaseIdx}|${Math.floor(t / (10 * 60_000))}`) * 8;
}

/**
 * Isil model: dT = K * I^2 (rapor 6.5 L1-1, tau*dDT/dt+DT=K*I^2'nin kararli hali).
 * K0 nokta basina sabit taban direnc; K_ratio = K/K0 (telemetrideki k_ratio alaninin ta kendisi).
 * Boylece I^2-dT sacilim grafiginde egim gercekten K_ratio ile birlikte degisir.
 */
function connPointValue(panoId: string, pt: string, field: string, t: number): number | null {
  const now = Date.now();
  const phase = phaseLetterOf(pt);
  const baseDt = 6 + 24 * noise(`dt0|${pt}`); // nokta basina hedef taban dT (tipik yukte), cesitlilik icin

  let kRatio = 1.0 + signedNoise(`${panoId}|${pt}|k0`) * 0.06;
  if (panoId === LOOSE_CONN.panoId && pt === LOOSE_CONN.point) {
    const start = now - LOOSE_CONN.days * DAY_MS;
    kRatio = rampAt(t, start, now, LOOSE_CONN.kFrom, LOOSE_CONN.kTo) + signedNoise(`k|${t}`) * 0.012;
  }

  let dt: number;
  if (phase != null) {
    const current = phaseCurrentA(panoId, PHASE_LETTER_INDEX[phase], t);
    const typicalCurrent = (350 + 500 * noise(`amp|${panoId}`)) * 0.6; // dailyLoad'un kaba ortalamasi
    const k0 = baseDt / typicalCurrent ** 2; // K0: taban direnc, dt=K0*I^2 esitliginden geriye cozulur
    dt = k0 * kRatio * current ** 2;
  } else {
    // Notr gibi tek faza bagli olmayan noktalar: K_ratio yine de saklanir ama dT dogrudan uretilir.
    dt = baseDt * kRatio + signedNoise(`${panoId}|${pt}|dt|${Math.floor(t / HOUR_MS)}`) * 0.6;
  }

  switch (field) {
    case "t_c":
      return +(AMBIENT_C + dt).toFixed(2);
    case "dt_c":
      return +dt.toFixed(2);
    case "k_ratio":
      return +kRatio.toFixed(3);
    case "tau_s":
      return 900;
    case "ttl_h":
      return kRatio > 1.3 ? Math.max(0, 336 - (kRatio - 1.3) * 600) : null;
    default:
      return null;
  }
}

function elecValue(panoId: string, field: string, index: string | undefined, t: number): number | null {
  if (field === "i_ph" && index != null) return Math.round(phaseCurrentA(panoId, Number(index), t));
  const seedAmp = 350 + 500 * noise(`amp|${panoId}`);
  const overload = panoId === "GDZ-00088";
  const load = dailyLoad(t) * (overload ? 3.9 : 1);
  if (field === "i_n") return Math.round(seedAmp * load * 0.08);
  if (field === "u_ph") return +(230 + signedNoise(`u|${panoId}|${index}|${t}`) * 1.2).toFixed(1);
  if (field === "thd_i") return +(5 + 2 * noise(`thd|${panoId}|${index}`)).toFixed(1);
  if (field === "cosphi") return 0.96;
  if (field === "unbal_pct") return +(3 + 3 * noise(`unbal|${panoId}`)).toFixed(1);
  return null;
}

function envValue(panoId: string, field: string, t: number): number | null {
  const now = Date.now();
  const humid = dailyHumidity(t);
  const condensing = panoId === CONDENSE.panoId && t > now - CONDENSE.days * DAY_MS;

  switch (field) {
    case "t_low_c":
      return +(22 + 6 * (1 - humid)).toFixed(1);
    case "rh_low_pct": {
      const base = 55 + 25 * humid;
      return +(condensing ? Math.min(98, base + 15 * humid) : base).toFixed(0);
    }
    case "td_margin_k":
      return +(condensing ? 3.5 - 2.8 * humid : 6 + 3 * (1 - humid)).toFixed(2);
    case "t_up_c":
      return +(28 + 6 * (1 - humid)).toFixed(1);
    case "rh_up_pct":
      return +(40 + 15 * humid).toFixed(0);
    case "dt_air_k":
      return +(7 + signedNoise(`dtair|${t}`) * 1.5).toFixed(1);
    default:
      return null;
  }
}

function tvocValue(panoId: string, field: string, t: number): number | null {
  const now = Date.now();
  if (panoId === ARC_EVENT.panoId) {
    const tripped = t >= now - ARC_EVENT.occurredAgoMs;
    if (field === "trips") return tripped ? 1 : 0;
    if (field === "prot_health_ok") return 1;
  }
  if (panoId === PROT_HEALTH.panoId) {
    const broken = t >= now - PROT_HEALTH.stepAgoMs;
    if (field === "prot_health_ok") return broken ? 0 : 1;
    if (field === "trips") return 0;
  }
  if (field === "trips") return 0;
  if (field === "prot_health_ok") return 1;
  return null;
}

function riskValue(panoId: string, t: number): number {
  const now = Date.now();
  if (panoId === ARC_EVENT.panoId) {
    return t >= now - ARC_EVENT.occurredAgoMs ? 95 : t >= now - ARC_EVENT.precursorAgoMs ? 22 : 8;
  }
  if (panoId === PROT_HEALTH.panoId) return t >= now - PROT_HEALTH.stepAgoMs ? 88 : 6;
  if (panoId === LOOSE_CONN.panoId) {
    return Math.round(rampAt(t, now - LOOSE_CONN.days * DAY_MS, now, 15, 72));
  }
  return Math.round(10 + 20 * noise(`risk|${panoId}`));
}

/** contracts/openapi.yaml serisindeki tek bir deger; bilinmeyen etiket icin null (bosluk). */
export function seriesPoint(panoId: string, tag: string, tMs: number): number | null {
  const [group, a, b] = tag.split(".");
  switch (group) {
    case "t_conn":
      return connPointValue(panoId, a, b, tMs);
    case "elec":
      return elecValue(panoId, a, b, tMs);
    case "env":
      return envValue(panoId, a, tMs);
    case "tvoc":
      return tvocValue(panoId, a, tMs);
    case "risk":
      return a === "score" ? riskValue(panoId, tMs) : null;
    default:
      return null;
  }
}

/** Backend'deki bucket_starts ile ayni mantik: adima hizali kovalar, [baslangic, bitis). */
export function bucketStarts(fromMs: number, toMs: number, stepMs: number): number[] {
  const first = Math.floor(fromMs / stepMs) * stepMs;
  const out: number[] = [];
  for (let t = first; t < toMs; t += stepMs) out.push(t);
  return out;
}

export function stepToMs(step: string): number {
  const match = /^(\d+)([smhd])$/.exec(step);
  if (!match) return 60_000;
  const mult: Record<string, number> = { s: 1000, m: 60_000, h: HOUR_MS, d: DAY_MS };
  return Number(match[1]) * mult[match[2]];
}
