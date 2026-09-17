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

export interface AckBody {
  by: string;
  note?: string;
  channel?: "ui" | "sms" | "scada";
}

export interface ShelveBody {
  by: string;
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
  fleetHealth?(limit?: number, signal?: AbortSignal): Promise<FleetHealthItem[]>;
  ack(alarmId: string, body: AckBody): Promise<{ ok?: boolean }>;
  alarms(query?: AlarmQuery, signal?: AbortSignal): Promise<Alarm[]>;
  shelve(alarmId: string, body: ShelveBody): Promise<{ ok?: boolean }>;
  series(panoId: string, tags: string[], from: Date, to: Date, step?: string, signal?: AbortSignal): Promise<SeriesResponse>;
  blackbox(eventId: string, windowH?: number, signal?: AbortSignal): Promise<Blackbox>;
}
