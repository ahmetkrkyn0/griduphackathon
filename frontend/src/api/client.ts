import { ApiError } from "./errors";
import { mockApi } from "./mock";
import { authHeader, clearToken } from "./session";
import type { AckBody, Alarm, Api, AssetFleet, AuthStatus, Blackbox, FleetKpi, OutageEvent, PanelDetail, PanelHealth, PanelSummary, SeriesResponse, ShelveBody } from "./types";

export const usingMocks = import.meta.env.VITE_USE_MOCKS === "1";

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  // F-19: belirtec varsa HER istege eklenir. Okuma uclari bugun belirtec istemiyor
  // (bilincli sinir, docs/15 §5) ama ileride isterse tek yer degisir.
  const headers: Record<string, string> = { Accept: "application/json", ...authHeader() };
  if (init.body) headers["Content-Type"] = "application/json";
  const res = await fetch(path, { ...init, headers });
  if (res.status === 401) {
    // Belirtec yok veya gecersiz: sakli olani at ki giris kapisi yeniden cizilsin.
    clearToken();
  }
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = (await res.json()) as { detail?: unknown };
      if (typeof body.detail === "string") detail = body.detail;
    } catch {
      // Govdesiz veya JSON olmayan hata yaniti: statusText yeterli.
    }
    throw new ApiError(res.status, detail);
  }
  return (await res.json()) as T;
}

// Goreli yollar: gelistirmede Vite proxy'si, uretimde nginx ayni kokenden backend'e iletir.
const httpApi: Api = {
  panels: (signal) => request<PanelSummary[]>("/api/v1/panels?sort=risk&limit=2000", { signal }),
  panel: (panoId, signal) => request<PanelDetail>(`/api/v1/panels/${encodeURIComponent(panoId)}`, { signal }),
  fleetKpi: (signal) => request<FleetKpi>("/api/v1/fleet/kpi", { signal }),
  fleetHealth: (signal) => request<PanelHealth[]>("/api/v1/fleet/health", { signal }),
  fleetAssets: (signal) => request<AssetFleet>("/api/v1/fleet/assets", { signal }),
  outages: (state = "acik", signal) => request<OutageEvent[]>(`/api/v1/outages?state=${state}`, { signal }),
  authStatus: async (signal) => {
    const body = await request<{ auth?: AuthStatus }>("/health", { signal });
    // Eski bir backend `auth` blogunu hic gondermeyebilir; o durumda "kapali" varsayilir
    // ve arayuz kullaniciya giris teklif etmez (yanlis bir kapi cizmektense sessiz kal).
    return body.auth ?? { enabled: false, users: [], protects: [] };
  },
  ack: (alarmId, body: AckBody) =>
    request<{ ok?: boolean }>(`/api/v1/alarms/${encodeURIComponent(alarmId)}/ack`, {
      method: "POST",
      body: JSON.stringify(body),
    }),
  shelve: (alarmId, body: ShelveBody) =>
    request<{ ok?: boolean }>(`/api/v1/alarms/${encodeURIComponent(alarmId)}/shelve`, {
      method: "POST",
      body: JSON.stringify(body),
    }),
  alarms: (query, signal) => {
    const params = new URLSearchParams();
    if (query?.state) params.set("state", query.state);
    if (query?.prio) params.set("prio", query.prio);
    if (query?.pano_id) params.set("pano_id", query.pano_id);
    if (query?.limit) params.set("limit", String(query.limit));
    const qs = params.toString();
    return request<Alarm[]>(`/api/v1/alarms${qs ? `?${qs}` : ""}`, { signal });
  },
  series: (panoId, tags, from, to, step, signal) => {
    const params = new URLSearchParams({ tags: tags.join(","), from: from.toISOString(), to: to.toISOString() });
    if (step) params.set("step", step);
    return request<SeriesResponse>(`/api/v1/panels/${encodeURIComponent(panoId)}/series?${params}`, { signal });
  },
  blackbox: (eventId, windowH, signal) => {
    const params = windowH ? `?window_h=${windowH}` : "";
    return request<Blackbox>(`/api/v1/events/${encodeURIComponent(eventId)}/blackbox${params}`, { signal });
  },
};

export const api: Api = usingMocks ? mockApi : httpApi;
