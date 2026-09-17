import { ApiError } from "./errors";
import { mockApi } from "./mock";
import type { AckBody, Alarm, Api, Blackbox, FleetHealthItem, FleetKpi, PanelDetail, PanelSummary, SeriesResponse, ShelveBody } from "./types";

export const usingMocks = import.meta.env.VITE_USE_MOCKS === "1";

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers: Record<string, string> = { Accept: "application/json" };
  if (init.body) headers["Content-Type"] = "application/json";
  const res = await fetch(path, { ...init, headers });
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
  fleetHealth: (limit = 2000, signal) => request<FleetHealthItem[]>(`/api/v1/fleet/health?limit=${limit}`, { signal }),
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
