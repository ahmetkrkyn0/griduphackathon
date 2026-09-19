// contracts/openapi.yaml semalarinin TEK elle yazilmis karsiligi.
// Alan adi uydurulmaz; eksik alan contracts/changes/ ile istenir.
// Opsiyonel isaretli alanlar: backend'in gercek yaniti (backend/app/api/views.py)
// telemetri yukunu oldugu gibi aktardigi icin her zaman dolu gelmeyebilir.

export type Prio = "P1" | "P2" | "P3" | "INFO" | "SYS";
export type PointState = "normal" | "warn" | "alarm" | "critical" | "stale";
export type AlarmState = "active" | "acked" | "shelved" | "cleared";
export type NotifyChannel = "sms" | "whatsapp" | "call" | "scada" | "relay";

export interface PanelSummary {
  pano_id: string;
  name: string;
  lat?: number | null;
  lon?: number | null;
  pano_type?: string;
  risk_score: number;
  risk_mode: string;
  risk_trend?: "up" | "flat" | "down";
  top_alarm: string | null;
  top_prio: Prio | null;
  ttl_h: number | null;
  last_seen: string;
  comms_ok: boolean;
  baseline_day?: number;
  /**
   * Varlik kutugu (F-21) — ozete giren UC alan. null = "CBS aktarimi yapilmadi",
   * SIFIR DEGIL. Bu yuzden `| null` tasirlar, `?` degil: eksik alan ile bilinmeyen
   * deger karistirilmamali (PanelHealth'te de ayni kural yazili).
   */
  abone_sayisi?: number | null;
  kritiklik?: Kritiklik | null;
  sonraki_bakim_at?: string | null;
}

/** AssetRegistry.kritiklik sozlugu. CBS'den ICE AKTARILAN etiket; bizim tanimimiz degil. */
export type Kritiklik = "kritik" | "yuksek" | "orta" | "dusuk";

/**
 * GET /fleet/assets satirindaki kunye (F-21).
 *
 * Kunyesi ice aktarilmamis pano icin `asset` alani null'dur — hepsi null olan bir nesne
 * DEGIL. Ekran bos hucre gostermek yerine "CBS'den ice aktarilmadi" yazabilsin diye.
 * `uretici` ve `seri_no` UYDURULMAZ; aktarim doldurmadiysa null kalir.
 */
export interface AssetRegistry {
  cbs_kodu: string | null;
  fider_id: string | null;
  il: string | null;
  ilce: string | null;
  abone_sayisi: number | null;
  trafo_kva: number | null;
  kritiklik: Kritiklik | null;
  uretici: string | null;
  seri_no: string | null;
  son_bakim_at: string | null;
  sonraki_bakim_at: string | null;
  kunye_kaynak: string | null;
  kunye_at: string | null;
}

/** Kapsama SAYIYLA verilir ki eksiklik gizlenemesin (GK10). */
export interface AssetCoverage {
  panolar: number;
  kunyeli: number;
  fiderli?: number;
  aboneli?: number;
}

/**
 * Ust sebeke kesintisi (F-22): ayni fiderde es zamanli susan N panonun TEK olayi.
 *
 * Bu bir ALARM DEGILDIR — alarmlari aciklayan bir olaydir. Alt alarmlar
 * (ALM-LASTGASP, ALM-COMMS-LOST) uretilmeye devam eder ve BASTIRILMAZ; yalnizca
 * `Alarm.outage_id` ile buna baglanir.
 */
export interface OutageEvent {
  outage_id: string;
  fider_id: string;
  /** Panolarin sustugu an — enerjinin kesildigi anin OLCULEBILEN en iyi yaklasimi. */
  started_at: string;
  /** Merkezin bagintiyi kurdugu an. */
  detected_at: string;
  /** Haberlesmenin GERI DONDUGU an. Enerjinin geri geldigi an DEGILDIR (histerezisli). */
  ended_at: string | null;
  state: "acik" | "kapandi";
  panolar: { pano_id: string; name?: string; last_rx: string; abone_sayisi: number | null }[];
  /** EPDK Madde 8/2 "etkilenen kullanici sayisi". null = hicbir panonun kunyesi yok. */
  abone_toplami?: number | null;
  /** Kunyesi olmadigi icin toplama giremeyen pano sayisi — gizlenmez. */
  abone_eksik?: number;
}

/** Madde 8/2'nin TEK bir alani (F-23). `durum` alanin ne oldugunu soyler. */
export interface EpdkAlan {
  ad: string;
  /** Olculen ya da onerilen deger; elle doldurulacaksa null. */
  deger: string | number | null;
  /**
   * olculen = bu depodan turetildi · oneri = sistem bir oneri uretti, KARAR DEGIL ·
   * elle_doldurulacak = bu alani OLCMUYORUZ
   */
  durum: "olculen" | "oneri" | "elle_doldurulacak";
  /** Degerin nereden geldigi ya da neden olcemedigimiz. Bos birakilmaz. */
  aciklama?: string;
}

/**
 * EPDK Kalite Yonetmeligi Madde 8/2 kesinti kaydi TASLAGI (F-23).
 *
 * Cikti TASLAKTIR ve bu, yapinin kendisidir: alan yanittan HICBIR ZAMAN dusurulmez —
 * olcmedigimiz alani cikarmak "bu alani olcmuyoruz" bilgisini de kaybettirirdi.
 */
export interface EpdkKaydi {
  /** HER ZAMAN true. Bu cikti resmi bir kayit DEGILDIR. */
  taslak: boolean;
  uyari: string;
  outage_id: string;
  alanlar: EpdkAlan[];
  ozet: { toplam: number; olculen: number; oneri: number; elle_doldurulacak: number };
  /** Kanit: MEVCUT kara kutu olayina baglanti. Yeni cizelge URETILMEZ (F-02 zaten 336 saat). */
  kanit?: { pano_id: string; name?: string; event_id: string | null; blackbox: string | null }[];
}

export interface AssetFleet {
  kapsama: AssetCoverage;
  panolar: { pano_id: string; name?: string; asset: AssetRegistry | null }[];
}

export interface ConnPoint {
  pt: string;
  label?: string;
  t_c: number;
  dt_c: number;
  k?: number | null;
  k_ratio?: number | null;
  tau_s?: number | null;
  ttl_h?: number | null;
  excited?: boolean;
  q?: number;
  state?: PointState;
}

export interface Env {
  t_low_c?: number;
  rh_low_pct?: number;
  td_low_c?: number;
  td_margin_k?: number;
  t_up_c?: number;
  rh_up_pct?: number;
  dt_air_k?: number;
  voc_idx?: number | null;
  door_open?: boolean;
}

export interface Elec {
  i_ph?: number[];
  i_n?: number;
  u_ph?: number[];
  thd_i?: number[];
  cosphi?: number;
  unbal_pct?: number;
  mpr_comm_ok?: boolean;
}

export interface Tvoc {
  trips?: number;
  state?: number;
  last_trip_at?: string | null;
  last_det_label?: string | null;
  prot_health_ok?: boolean;
  comm_ok?: boolean;
}

export interface DeviceHealth {
  uptime_s?: number;
  nodes_ok?: number;
  nodes_total?: number;
  rssi_dbm?: number;
  vbak_pct?: number;
  buffered?: number;
  maint_mode?: boolean;
  fw?: string;
  baseline_day?: number;
}

export interface AlarmSignal {
  tag: string;
  value: number;
  threshold?: number | null;
  unit?: string;
}

/**
 * Karsi-olgusal aciklama blogu: baskin hipotezin bu ornekte HENUZ GORULMEYEN kaniti
 * (backend/app/risk.py `_verify`). contracts/openapi.yaml DONMUS oldugu icin yeni bir
 * yanit alani acilmadi; sozlesmedeki AlarmReason acik bir nesnedir
 * (additionalProperties kapali degil) ve blok onun icinde tasinir.
 */
export interface AlarmVerify {
  /** hypotheses[].code, or. "HYP-LOOSE-CONN". */
  hypothesis: string;
  /** Bu ornekte gorulmeyen kanit kodlari, sozlesmedeki sirayla. */
  missing: string[];
  /** Hipotezin sozlesmedeki toplam kanit sayisi. */
  total: number;
}

export interface AlarmReason {
  signals?: AlarmSignal[];
  layer?: "L-1" | "L0" | "L1" | "L2" | "L3";
  basis?: string;
  point?: string | null;
  verify?: AlarmVerify;
}

export interface Alarm {
  /** Alarm bir ust sebeke kesintisine baglandiysa o kesintinin kimligi (F-22). BASTIRMA DEGILDIR. */
  outage_id?: string | null;
  id: string;
  event_id?: string | null;
  pano_id: string;
  code: string;
  text?: string;
  prio: Prio;
  state: AlarmState;
  raised_at: string;
  cleared_at?: string | null;
  acked_at?: string | null;
  acked_by?: string | null;
  shelved_until?: string | null;
  escalation_level?: number;
  notified?: NotifyChannel[];
  reason?: AlarmReason | null;
  advice?: string;
  ttl_h?: number | null;
}

export interface PanelDetail {
  pano_id: string;
  name?: string;
  pano_type?: string;
  ts: string;
  risk_score?: number;
  risk_mode?: string;
  risk_contributions?: Record<string, number>;
  points: ConnPoint[];
  env: Env;
  elec: Elec;
  tvoc?: Tvoc;
  pd?: Record<string, unknown> | null;
  health: DeviceHealth;
  active_alarms?: Alarm[];
  /** Varlik kunyesi (F-21). CBS aktarimi yapilmamissa null. */
  asset?: AssetRegistry | null;
}

/**
 * GET /fleet/health satiri (Cihaz Sagligi ekrani).
 *
 * Alanlar null OLABILIR ve bu "0" ile ayni sey degildir: veri gondermemis bir pano
 * icin null gelir, 0 dBm ise gecerli bir RSSI'dir. Bu yuzden tipler `| null` tasir,
 * `?` degil — eksik alan ile bilinmeyen deger karistirilmasin.
 */
export interface PanelHealth {
  pano_id: string;
  name: string;
  nodes_ok: number | null;
  nodes_total: number | null;
  rssi_dbm: number | null;
  vbak_pct: number | null;
  buffered: number | null;
  maint_mode: boolean | null;
  fw: string | null;
  baseline_day: number;
  last_seen: string;
  comms_ok: boolean;
}

/** GET /health `auth` blogu (F-19). */
export interface AuthStatus {
  enabled: boolean;
  users: string[];
  protects: string[];
}

export interface FleetKpi {
  panels_total?: number;
  comms_ok_pct?: number;
  alarms_per_100_panels_per_day?: number;
  active_by_prio?: Record<string, number>;
  distribution_pct?: Record<string, number>;
  p95_end_to_end_ms?: number;
  ingest_msgs_per_s?: number;
}

/**
 * F-19: `by` alani KALDIRILDI. Onaylayanin adi sunucuda, dogrulanmis Authorization
 * basligindan turer (openapi v1.2.0). Buraya bir ad yazmak hicbir sey degistirmez —
 * sunucu govdedeki `by`'yi yok sayar.
 */
export interface AckBody {
  note?: string;
  channel?: "ui" | "sms" | "scada";
}

export interface ShelveBody {
  minutes: number;
  reason: string;
}

export interface AlarmQuery {
  /** Virgülle ayrılmış durumlar; backend varsayılanı "active,acked". */
  state?: string;
  /** Virgülle ayrılmış öncelikler, ör. "P1,P2". */
  prio?: string;
  pano_id?: string;
  limit?: number;
}

/** {tag: [[unix_ms, deger|null]]}; bkz. GET /panels/{id}/series. */
export type SeriesResponse = Record<string, Array<[number, number | null]>>;

export interface TimelineEntry {
  ts: string;
  kind: "alarm" | "ack" | "action" | "note" | "trip";
  text: string;
}

export interface Blackbox {
  event_id: string;
  pano_id: string;
  occurred_at: string;
  code: string;
  det_label: string | null;
  window_h: number;
  series: SeriesResponse;
  timeline: TimelineEntry[];
}

// openapi.yaml x-websocket. Backend: main.py "tel" -> panel_summary, alarm_service.py "alarm" -> alarm_view.
export type StreamMessage =
  | { type: "hello"; payload: { server_time: string; api_version: string } }
  | { type: "tel"; payload: PanelSummary }
  | { type: "alarm"; payload: Alarm }
  | { type: "kpi"; payload: FleetKpi };

/**
 * GET /fleet/health satirinin GEVSEK karsiligi (main). Canli uc PanelHealth dondurur —
 * bu tip onun alt kumesidir (maint_mode yok, name/baseline_day opsiyonel). Sozlesmeyi
 * gevsetmemek icin Api.fleetHealth PanelHealth kullanir; tip, ucu daha az varsayimla
 * tuketen kodu kirmamak adina birakildi.
 */
export interface FleetHealthItem {
  pano_id: string;
  name?: string;
  nodes_ok: number | null;
  nodes_total: number | null;
  rssi_dbm: number | null;
  vbak_pct: number | null;
  buffered: number | null;
  fw: string | null;
  comms_ok: boolean;
  last_seen: string;
  baseline_day?: number | null;
}

export interface Api {
  panels(signal?: AbortSignal): Promise<PanelSummary[]>;
  panel(panoId: string, signal?: AbortSignal): Promise<PanelDetail>;
  fleetKpi(signal?: AbortSignal): Promise<FleetKpi>;
  /**
   * Toplu cihaz sagligi (GET /fleet/health).
   *
   * `limit` YOKTUR: backend bu ucta sayfalama parametresi okumaz, yollamak yaniltici olurdu.
   * Donen satir PanelHealth'tir (maint_mode ve baseline_day dahil, alanlar `| null`).
   * Isaret opsiyoneldir cunku Cihaz Sagligi ekrani ucu desteklemeyen bir backend'e karsi
   * pano-basina cekime dusuyor; o geri-uyum yolu bu kontrol ile seciliyor.
   */
  fleetHealth?(signal?: AbortSignal): Promise<PanelHealth[]>;
  fleetAssets(signal?: AbortSignal): Promise<AssetFleet>;
  outages(state?: "acik" | "hepsi", signal?: AbortSignal): Promise<OutageEvent[]>;
  epdkKaydi(outageId: string, signal?: AbortSignal): Promise<EpdkKaydi>;
  authStatus(signal?: AbortSignal): Promise<AuthStatus>;
  ack(alarmId: string, body: AckBody): Promise<{ ok?: boolean }>;
  alarms(query?: AlarmQuery, signal?: AbortSignal): Promise<Alarm[]>;
  shelve(alarmId: string, body: ShelveBody): Promise<{ ok?: boolean }>;
  series(panoId: string, tags: string[], from: Date, to: Date, step?: string, signal?: AbortSignal): Promise<SeriesResponse>;
  blackbox(eventId: string, windowH?: number, signal?: AbortSignal): Promise<Blackbox>;
}
