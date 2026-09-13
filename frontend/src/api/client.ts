import { ApiError } from "./errors";
import { mockApi } from "./mock";
import type { AckBody, Api, FleetKpi, PanelDetail, PanelSummary } from "./types";

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
  ack: (alarmId, body: AckBody) =>
    request<{ ok?: boolean }>(`/api/v1/alarms/${encodeURIComponent(alarmId)}/ack`, {
      method: "POST",
      body: JSON.stringify(body),
    }),
};

export const api: Api = usingMocks ? mockApi : httpApi;
